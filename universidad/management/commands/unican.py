from pathlib import Path
import csv

from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

from universidad.models import Area, Universidad, Titulo, Asignatura


class Command(BaseCommand):
    help = (
        "Importa datos desde un CSV (por defecto fixtures/unican.csv) y crea "
        "Titulos y Asignaturas.\n\n"
        "- Asignatura.name = title\n"
        "- Asignatura.slug = slugify(title)\n"
        "- Titulo.name = BacherlorsDegree\n"
        "- Titulo.slug = slugify(BacherlorsDegree)\n"
        "- Titulo.universidad = Universidad con id indicado (por defecto 1)\n"
        "- Titulo.area = Area con id indicado (por defecto 1)\n"
        "- Asignatura.titulo = Titulo creado/recuperado de la misma fila\n"
        "- No se duplican Titulos: se compara por slug + universidad + area"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv-path",
            type=str,
            default="fixtures/unican.csv",
            help="Ruta al CSV de entrada (default: fixtures/unican.csv).",
        )
        parser.add_argument(
            "--universidad-id",
            type=int,
            default=1,
            help=(
                "ID de la Universidad que se asignará a todos los Titulos "
                "(default: 1)."
            ),
        )
        parser.add_argument(
            "--area-id",
            type=int,
            default=1,
            help="ID del Area que se asignará a todos los Titulos (default: 1).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Muestra lo que haría sin escribir en la base de datos.",
        )

    def handle(self, *args, **options):
        csv_path = Path(options["csv_path"])
        universidad_id = options["universidad_id"]
        area_id = options["area_id"]
        dry_run = options["dry_run"]

        if not csv_path.is_file():
            raise CommandError(f"No se encuentra el CSV: {csv_path}")

        try:
            universidad = Universidad.objects.get(pk=universidad_id)
        except Universidad.DoesNotExist as exc:
            raise CommandError(f"No existe Universidad con id={universidad_id}") from exc

        try:
            area = Area.objects.get(pk=area_id)
        except Area.DoesNotExist as exc:
            raise CommandError(f"No existe Area con id={area_id}") from exc

        self.stdout.write(
            self.style.NOTICE(
                f"Usando CSV: {csv_path} | "
                f"Universidad id={universidad.pk} ({universidad.name}) | "
                f"Area id={area.pk} ({area.name}) | "
                f"dry_run={dry_run}"
            )
        )

        created_titulos = 0
        created_asignaturas = 0

        required_columns = ["title", "BacherlorsDegree"]

        with csv_path.open(encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f, delimiter=";")
            if not reader.fieldnames:
                raise CommandError("El CSV no tiene cabecera.")

            missing = [c for c in required_columns if c not in reader.fieldnames]
            if missing:
                raise CommandError(
                    "Faltan columnas en el CSV: "
                    + ", ".join(missing)
                    + f". Encontradas: {reader.fieldnames}"
                )

            for index, row in enumerate(reader, start=1):
                # CSV.title → Asignatura
                raw_asignatura = (row.get("title") or "").strip().strip('"')
                # CSV.BacherlorsDegree → Titulo
                raw_titulo = (row.get("BacherlorsDegree") or "").strip().strip('"')

                if not raw_asignatura and not raw_titulo:
                    continue

                titulo_slug = slugify(raw_titulo) if raw_titulo else None
                asignatura_slug = slugify(raw_asignatura) if raw_asignatura else None

                if dry_run:
                    self.stdout.write(
                        f"[dry-run] Fila {index}: "
                        f"Titulo.name='{raw_titulo}' slug='{titulo_slug}' | "
                        f"Asignatura.name='{raw_asignatura}' slug='{asignatura_slug}'"
                    )
                    continue

                # Titulo: deduplicar por slug + universidad + area.
                # Si ya existe un Titulo con ese slug en esa universidad/area NO se crea otro.
                if not titulo_slug:
                    # Si no hay texto de grado, no podemos crear título; en ese caso
                    # no creamos título ni asignatura.
                    continue

                titulo, titulo_created = Titulo.objects.get_or_create(
                    slug=titulo_slug,
                    universidad=universidad,
                    area=area,
                    defaults={
                        "name": raw_titulo,
                    },
                )
                if titulo_created:
                    created_titulos += 1

                # Asignatura: deduplicar por slug + titulo
                asignatura, asignatura_created = Asignatura.objects.get_or_create(
                    titulo=titulo,
                    slug=asignatura_slug,
                    defaults={
                        "name": raw_asignatura,
                    },
                )
                if asignatura_created:
                    created_asignaturas += 1

        if dry_run:
            self.stdout.write(self.style.SUCCESS("Dry-run completado."))
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Importación completada. "
                    f"Nuevos Titulos: {created_titulos} | "
                    f"Nuevas Asignaturas: {created_asignaturas}"
                )
            )
