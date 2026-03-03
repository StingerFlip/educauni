from pathlib import Path
import csv

from django.core.management.base import BaseCommand, CommandError

from universidad.models import Area, Titulo, Asignatura


class Command(BaseCommand):
    help = (
        "Importa datos desde un CSV (por defecto fixtures/unican.csv) y crea "
        "Titulos y Asignaturas.\n\n"
        "- Titulo.name = title\n"
        "- Asignatura.name = BacherlorsDegree\n"
        "- Titulo.area = Area con id indicado (por defecto 1)\n"
        "- Asignatura.titulo = Titulo creado/recuperado de la misma fila"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv-path",
            type=str,
            default="fixtures/unican.csv",
            help="Ruta al CSV de entrada (default: fixtures/unican.csv).",
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
        area_id = options["area_id"]
        dry_run = options["dry_run"]

        if not csv_path.is_file():
            raise CommandError(f"No se encuentra el CSV: {csv_path}")

        try:
            area = Area.objects.get(pk=area_id)
        except Area.DoesNotExist as exc:
            raise CommandError(f"No existe Area con id={area_id}") from exc

        self.stdout.write(
            self.style.NOTICE(
                f"Usando CSV: {csv_path} | Area id={area.pk} ({area.name}) "
                f"| dry_run={dry_run}"
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
                raw_title = (row.get("title") or "").strip().strip('"')
                raw_degree = (row.get("BacherlorsDegree") or "").strip().strip('"')

                if not raw_title and not raw_degree:
                    continue

                if dry_run:
                    self.stdout.write(
                        f"[dry-run] Fila {index}: "
                        f"Titulo.name='{raw_title}' | "
                        f"Asignatura.name='{raw_degree}'"
                    )
                    continue

                titulo, titulo_created = Titulo.objects.get_or_create(
                    name=raw_title,
                    area=area,
                )
                if titulo_created:
                    created_titulos += 1

                asignatura, asignatura_created = Asignatura.objects.get_or_create(
                    titulo=titulo,
                    name=raw_degree,
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

