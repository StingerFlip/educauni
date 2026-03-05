from __future__ import annotations

import csv
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
import re
from typing import Iterable, List, Tuple
from urllib.parse import urlencode
import xml.etree.ElementTree as ET

import certifi
import requests
from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

from universidad.models import Area, Universidad, Titulo, Asignatura


BASE_URL = (
    "https://servicios.urjc.es/guiasdocentes/getAsignaturasAlumnoAjax.jsp"
)


@dataclass
class PlanOption:
    cod_plan: str
    nombre: str


class OptionParser(HTMLParser):
    """Sencillo parser HTML para extraer <option value='X'>Texto</option>."""

    def __init__(self) -> None:
        super().__init__()
        self._current_value: str | None = None
        self._current_text_parts: List[str] = []
        self.options: List[PlanOption] = []

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, str]]) -> None:
        if tag.lower() == "option":
            attrs_dict = dict(attrs)
            self._current_value = attrs_dict.get("value")
            self._current_text_parts = []

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "option" and self._current_value is not None:
            text = "".join(self._current_text_parts).strip()
            if self._current_value and text:
                self.options.append(
                    PlanOption(cod_plan=self._current_value, nombre=text)
                )
            self._current_value = None
            self._current_text_parts = []

    def handle_data(self, data: str) -> None:
        if self._current_value is not None and data:
            self._current_text_parts.append(data)


def load_plan_options(path: Path) -> List[PlanOption]:
    if not path.is_file():
        raise CommandError(f"No se encuentra el fichero de planes: {path}")

    parser = OptionParser()
    parser.feed(path.read_text(encoding="utf-8"))
    return parser.options


def load_areas_by_id() -> dict[int, Area]:
    areas = Area.objects.all()
    if not areas:
        raise CommandError("No hay áreas definidas en la base de datos.")
    return {area.id: area for area in areas}


AREA_KEYWORDS: dict[int, List[str]] = {
    # 1: Artes y Humanidades
    1: [
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
    ],
    # 2: Ciencias
    2: [
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
    ],
    # 3: Ciencias de la Salud
    3: [
        "medicin",
        "enfermer",
        "psicolog",
        "fisioterap",
        "odontolog",
        "farmacia",
        "podolog",
        "alimentos",
        "alimentari",
    ],
    # 4: Derecho
    4: [
        "derecho",
        "jurídic",
        "juridic",
    ],
    # 5: Ingeniería y Arquitectura
    5: [
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
    ],
    # 6: Educación
    6: [
        "educación",
        "educacion",
        "magisterio",
        "pedagog",
        "docencia",
        "profesorado",
    ],
    # 7: Ciencias Políticas
    7: [
        "polític",
        "politic",
        "relaciones internacionales",
        "diplomac",
        "estudios globales",
    ],
    # 9: Ciencias Sociales
    9: [
        "sociolog",
        "trabajo social",
        "comunicación",
        "comunicacion",
        "periodismo",
        "protocolo",
        "turismo",
        "criminolog",
        "igualdad de género",
        "igualdad de genero",
    ],
    # 10: Música
    10: [
        "música",
        "musica",
    ],
    # 11: Economía y Empresa
    11: [
        "econom",
        "empresa",
        "marketing",
        "finanzas",
        "contabilidad",
        "ade",
        "dirección y gestión de empresas",
        "direccion y gestion de empresas",
    ],
}


def guess_area_id_for_title(nombre_titulo: str, available_area_ids: Iterable[int]) -> int:
    """Devuelve el id de área más razonable para un nombre de titulación."""
    title_lower = nombre_titulo.lower()

    for area_id, keywords in AREA_KEYWORDS.items():
        if area_id not in available_area_ids:
            continue
        for kw in keywords:
            if kw in title_lower:
                return area_id

    # Fallback: preferir Ciencias Sociales (9) si existe, si no el primer id disponible.
    if 9 in available_area_ids:
        return 9
    return sorted(available_area_ids)[0]


class Command(BaseCommand):
    help = (
        "Importa títulos y asignaturas desde la URJC usando el fichero "
        "fixtures/urjc/urjc.txt y la URL de guías docentes.\n\n"
        "- Universidad fija: id = 2 (URJC).\n"
        "- Área: se infiere del nombre de la titulación usando fixtures/universidad_area.csv.\n"
        "- No se excluyen másteres; se importan grados y másteres.\n"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--urjc-file",
            type=str,
            default="fixtures/urjc/urjc.txt",
            help="Ruta al fichero de <option> de planes URJC "
            "(default: fixtures/urjc/urjc.txt).",
        )
        parser.add_argument(
            "--curso-academico",
            type=str,
            default="2025-26",
            help="Valor del parámetro cursoAcademico (default: 2025-26).",
        )
        parser.add_argument(
            "--only-cod-plan",
            type=str,
            help="Si se indica, solo importa el plan con ese codPlan.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Muestra lo que haría sin escribir en la base de datos.",
        )

    def handle(self, *args, **options):
        urjc_file = Path(options["urjc_file"])
        curso_academico = options["curso_academico"]
        only_cod_plan = options["only_cod_plan"]
        dry_run = options["dry_run"]

        try:
            universidad = Universidad.objects.get(pk=2)
        except Universidad.DoesNotExist as exc:
            raise CommandError(
                "No existe Universidad con id=2. Crea primero la universidad "
                "URJC con id 2 o ajusta el modelo según tus necesidades."
            ) from exc

        areas_by_id = load_areas_by_id()

        self.stdout.write(
            self.style.NOTICE(
                f"URJC import: universidad id={universidad.pk} ({universidad.name}), "
                f"cursoAcademico={curso_academico}, dry_run={dry_run}"
            )
        )

        plan_options = load_plan_options(urjc_file)
        if only_cod_plan:
            plan_options = [
                p for p in plan_options if p.cod_plan == only_cod_plan
            ]
            if not plan_options:
                raise CommandError(
                    f"No se encontró ningún plan con codPlan={only_cod_plan} "
                    f"en {urjc_file}"
                )

        if not plan_options:
            raise CommandError("No se encontraron planes en el fichero URJC.")

        total_planes = len(plan_options)
        created_titulos = 0
        created_asignaturas = 0

        for idx, plan in enumerate(plan_options, start=1):
            # Nombre completo tal como viene del <option>, p.ej.
            # "GRADO EN ... (1º curso)" o "GRADO EN ... (2º, 3º Y 4º CURSO)"
            full_title = plan.nombre.strip()
            # Nombre base sin el sufijo de curso entre paréntesis para
            # tener un solo Titulo por grado.
            base_title = re.sub(r"\s*\([^)]*\)\s*$", "", full_title).strip()
            titulo_name = base_title or full_title
            titulo_slug = slugify(titulo_name)

            area_id = guess_area_id_for_title(
                titulo_name, available_area_ids=areas_by_id.keys()
            )
            area = areas_by_id[area_id]

            self.stdout.write(
                self.style.NOTICE(
                    f"[{idx}/{total_planes}] Plan codPlan={plan.cod_plan} "
                    f"→ '{full_title}' → base '{titulo_name}' (slug='{titulo_slug}') | área id={area.id} "
                    f"({area.name})"
                )
            )

            if dry_run:
                # En dry-run no llamamos a la red ni tocamos BD.
                continue

            # Crear/reutilizar Titulo (deduplicado por slug + universidad + area)
            titulo, titulo_created = Titulo.objects.get_or_create(
                slug=titulo_slug,
                universidad=universidad,
                area=area,
                defaults={"name": titulo_name},
            )
            if titulo_created:
                created_titulos += 1

            # Llamada a la URL de asignaturas para este plan (usando requests + certifi)
            params = {
                "codPlan": plan.cod_plan,
                "alumno": "1",
                "cursoAcademico": curso_academico,
            }
            url = f"{BASE_URL}?{urlencode(params)}"

            try:
                resp = requests.get(url, timeout=15, verify=certifi.where())
                resp.raise_for_status()
                content = resp.text
            except requests.RequestException as exc:
                self.stderr.write(
                    self.style.WARNING(
                        f"  Error HTTP/SSL al obtener asignaturas para "
                        f"codPlan={plan.cod_plan}: {exc}"
                    )
                )
                continue

            try:
                root = ET.fromstring(content)
            except ET.ParseError as exc:
                self.stderr.write(
                    self.style.WARNING(
                        f"  No se pudo parsear el XML para codPlan={plan.cod_plan}: "
                        f"{exc}"
                    )
                )
                continue

            for node in root.findall("asignatura"):
                cod_asig = node.get("cod")
                nombre_asig = (node.text or "").strip()

                if not cod_asig or cod_asig == "Todas":
                    continue
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
                    f"Importación completada. Planes procesados: {total_planes}. "
                    f"Nuevos Titulos: {created_titulos}. "
                    f"Nuevas Asignaturas: {created_asignaturas}."
                )
            )

