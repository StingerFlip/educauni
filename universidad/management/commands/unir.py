from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Dict, Any

from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

from universidad.models import Area, Universidad, Titulo, Asignatura


@dataclass
class UnirCourse:
    course_name: str
    category: str
    plan: Dict[str, Any]
    source_path: Path


def load_areas_by_id() -> dict[int, Area]:
    areas = Area.objects.all()
    if not areas:
        raise CommandError("No hay áreas definidas en la base de datos.")
    return {area.id: area for area in areas}


def guess_area_id_from_category_or_title(
    category: str, title: str, available_area_ids: Iterable[int]
) -> int:
    cat = (category or "").lower()
    title_lower = title.lower()

    # Intentar casar directamente con nombres de áreas conocidas
    # apoyándonos en palabras clave de la categoría.
    # 5: Ingeniería y Arquitectura
    if 5 in available_area_ids and (
        "ingenier" in cat
        or "ingeniería" in cat
        or "arquitect" in cat
    ):
        return 5

    # 3: Ciencias de la Salud
    if 3 in available_area_ids and (
        "salud" in cat
        or "medicin" in cat
        or "enfermer" in cat
        or "psicolog" in cat
        or "nutric" in cat
    ):
        return 3

    # 6: Educación
    if 6 in available_area_ids and (
        "educación" in cat
        or "educacion" in cat
        or "magisterio" in cat
        or "pedagog" in cat
    ):
        return 6

    # 11: Economía y Empresa
    if 11 in available_area_ids and (
        "empresa" in cat
        or "econom" in cat
        or "marketing" in cat
        or "finanzas" in cat
    ):
        return 11

    # 9: Ciencias Sociales / Comunicación
    if 9 in available_area_ids and (
        "comunicación" in cat
        or "comunicacion" in cat
        or "social" in cat
        or "jurídic" in cat
        or "juridic" in cat
        or "politic" in cat
    ):
        return 9

    # Si por categoría no está claro, reusar heurística simple sobre el título.
    # 1: Artes y Humanidades
    if 1 in available_area_ids and any(
        kw in title_lower
        for kw in [
            "historia",
            "filosof",
            "arte",
            "artes",
            "bellas artes",
            "humanidad",
            "patrimonio",
            "traducción",
            "traduccion",
            "literatura",
        ]
    ):
        return 1

    # 2: Ciencias
    if 2 in available_area_ids and any(
        kw in title_lower
        for kw in [
            "biolog",
            "químic",
            "quimic",
            "físic",
            "fisic",
            "matemát",
            "matemat",
            "nanociencia",
            "nanotecnolog",
            "quimica",
        ]
    ):
        return 2

    # 3: Ciencias de la Salud (título)
    if 3 in available_area_ids and any(
        kw in title_lower
        for kw in [
            "medicin",
            "enfermer",
            "psicolog",
            "fisioterap",
            "odontolog",
            "farmacia",
            "podolog",
            "alimentos",
            "alimentari",
        ]
    ):
        return 3

    # 4: Derecho
    if 4 in available_area_ids and any(
        kw in title_lower for kw in ["derecho", "jurídic", "juridic"]
    ):
        return 4

    # 5: Ingeniería y Arquitectura (título)
    if 5 in available_area_ids and any(
        kw in title_lower
        for kw in [
            "ingenier",
            "arquitect",
            "robótica",
            "robotica",
            "videojuego",
            "telecomunic",
            "industrial",
            "energ",
            "materiales",
            "sistemas",
        ]
    ):
        return 5

    # 6: Educación (título)
    if 6 in available_area_ids and any(
        kw in title_lower
        for kw in [
            "educación",
            "educacion",
            "magisterio",
            "pedagog",
            "docencia",
            "profesorado",
        ]
    ):
        return 6

    # 7: Ciencias Políticas
    if 7 in available_area_ids and any(
        kw in title_lower
        for kw in [
            "polític",
            "politic",
            "relaciones internacionales",
            "diplomac",
            "estudios globales",
        ]
    ):
        return 7

    # 9: Ciencias Sociales (fallback preferido)
    if 9 in available_area_ids:
        return 9

    # Fallback final: primer id disponible
    return sorted(available_area_ids)[0]


def iter_unir_courses(dataset_dir: Path) -> List[UnirCourse]:
    if not dataset_dir.is_dir():
        raise CommandError(f"No existe el directorio de datasets de UNIR: {dataset_dir}")

    courses: List[UnirCourse] = []
    for path in sorted(dataset_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            # Si algún fichero está corrupto, lo saltamos pero avisamos
            # (no usamos stderr aquí para simplificar).
            continue

        course_name = data.get("course_name") or ""
        category = data.get("category") or ""
        plan = data.get("plan") or {}

        if not course_name:
            continue

        courses.append(
            UnirCourse(
                course_name=course_name,
                category=category,
                plan=plan,
                source_path=path,
            )
        )

    return courses


class Command(BaseCommand):
    help = (
        "Importa títulos y asignaturas desde los datasets de UNIR "
        "ubicados en fixtures/unir/dataset.\n\n"
        "- Titulo.name = course_name\n"
        "- Titulo.slug = slugify(course_name)\n"
        "- Area: se infiere a partir de category y del título.\n"
        "- Universidad: se crea/usa una entrada específica para UNIR.\n"
        "- Asignaturas: se leen de los planes anidados, deduplicadas por slug+título.\n"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dataset-dir",
            type=str,
            default="fixtures/unir/dataset",
            help="Directorio con los JSON de UNIR "
            "(default: fixtures/unir/dataset).",
        )
        parser.add_argument(
            "--only-course-contains",
            type=str,
            help="Si se indica, solo importa cursos cuyo course_name contenga este texto.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Muestra lo que haría sin escribir en la base de datos.",
        )

    def handle(self, *args, **options):
        dataset_dir = Path(options["dataset_dir"])
        only_course_contains: str | None = options["only_course_contains"]
        dry_run: bool = options["dry_run"]

        # Universidad UNIR (sin asumir id fija)
        unir_name = "Universidad Internacional de La Rioja"
        universidad, _ = Universidad.objects.get_or_create(
            name=unir_name,
            defaults={"description": "UNIR - Universidad Internacional de La Rioja"},
        )

        areas_by_id = load_areas_by_id()

        courses = iter_unir_courses(dataset_dir)
        if only_course_contains:
            fragment = only_course_contains.lower()
            courses = [
                c for c in courses if fragment in c.course_name.lower()
            ]

        if not courses:
            raise CommandError("No se encontraron cursos UNIR para importar.")

        total_cursos = len(courses)
        created_titulos = 0
        created_asignaturas = 0

        self.stdout.write(
            self.style.NOTICE(
                f"UNIR import: universidad id={universidad.pk} ({universidad.name}), "
                f"datasets en {dataset_dir}, dry_run={dry_run}"
            )
        )

        for idx, course in enumerate(courses, start=1):
            titulo_name = course.course_name.strip()
            titulo_slug = slugify(titulo_name)
            area_id = guess_area_id_from_category_or_title(
                category=course.category,
                title=titulo_name,
                available_area_ids=areas_by_id.keys(),
            )
            area = areas_by_id[area_id]

            self.stdout.write(
                self.style.NOTICE(
                    f"[{idx}/{total_cursos}] Curso '{titulo_name}' "
                    f"(category='{course.category}') "
                    f"→ área id={area.id} ({area.name})"
                )
            )

            if dry_run:
                # No tocamos BD ni procesamos asignaturas en detalle.
                continue

            titulo, titulo_created = Titulo.objects.get_or_create(
                slug=titulo_slug,
                universidad=universidad,
                area=area,
                defaults={"name": titulo_name},
            )
            if titulo_created:
                created_titulos += 1

            # Recorrer el plan para obtener todas las asignaturas
            plan = course.plan or {}
            for _, year_info in plan.items():
                periodos = (year_info or {}).get("periodos") or {}
                for _, periodo_info in periodos.items():
                    asignaturas = (periodo_info or {}).get("asignaturas") or []
                    for asig in asignaturas:
                        nombre_asig = (asig.get("name") or "").strip()
                        if not nombre_asig:
                            continue
                        asig_slug = slugify(nombre_asig)

                        asignatura, asignatura_created = Asignatura.objects.get_or_create(
                            titulo=titulo,
                            slug=asig_slug,
                            defaults={"name": nombre_asig},
                        )
                        if asignatura_created:
                            created_asignaturas += 1

        if dry_run:
            self.stdout.write(self.style.SUCCESS("Dry-run completado."))
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Importación UNIR completada. Cursos procesados: {total_cursos}. "
                    f"Nuevos Titulos: {created_titulos}. "
                    f"Nuevas Asignaturas: {created_asignaturas}."
                )
            )

