from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable, List

from django.core.management.base import BaseCommand
from django.db import models

from universidad.models import Asignatura


STOPWORDS: List[str] = [
    "de",
    "del",
    "la",
    "el",
    "en",
    "y",
    "para",
    "por",
    "con",
    "un",
    "una",
    "unos",
    "unas",
    "los",
    "las",
    "al",
    "lo",
    "se",
    "su",
    "sus",
    "a",
    "o",
]

ROMAN_NUMERALS: List[str] = [
    "i",
    "ii",
    "iii",
    "iv",
    "v",
    "vi",
    "vii",
    "viii",
    "ix",
    "x",
]


def build_keywords(text: str) -> str:
    """
    Dada la cadena de nombre de una asignatura, devuelve una cadena de
    palabras clave:
    - minúsculas
    - sin signos ni símbolos
    - sin stopwords, números ni numerales romanos
    - sin duplicados, respetando el orden de aparición
    - unidas por comas y espacio: "palabra1, palabra2, palabra3"
    """
    if not text:
        return ""

    # Normalización básica
    normalized = text.lower()
    # Reemplazar separadores habituales por espacio
    normalized = re.sub(r"[-/]", " ", normalized)
    # Eliminar signos de puntuación y símbolos (incluido *)
    normalized = re.sub(r"[.,;:!?()\\[\\]\"'¿¡*]", " ", normalized)

    tokens = normalized.split()
    if not tokens:
        return ""

    stopwords = set(STOPWORDS)
    roman = set(ROMAN_NUMERALS)

    seen = set()
    keywords: List[str] = []

    for token in tokens:
        if not token:
            continue

        # Quitar números puros
        if token.isdigit():
            continue

        # Quitar numerales romanos
        if token in roman:
            continue

        # Quitar palabras muy cortas (1-2 caracteres)
        if len(token) < 3:
            continue

        # Quitar stopwords
        if token in stopwords:
            continue

        if token in seen:
            continue

        seen.add(token)
        keywords.append(token)

    # Sin espacios, para poder hacer split directo por coma
    return ",".join(keywords)


class Command(BaseCommand):
    help = (
        "Genera el campo palabras_clave para las asignaturas a partir "
        "del nombre, filtrando stopwords, signos, numerales romanos, etc."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--only-empty",
            action="store_true",
            help="Solo procesa asignaturas con palabras_clave vacío o nulo.",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Vacía primero palabras_clave de las asignaturas seleccionadas.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            help="Máximo número de asignaturas a procesar (para pruebas).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Muestra los cambios que haría sin escribir en la base de datos.",
        )

    def handle(self, *args, **options):
        only_empty: bool = options["only_empty"]
        clear: bool = options["clear"]
        limit: int | None = options["limit"]
        dry_run: bool = options["dry_run"]

        # Quitar asteriscos del nombre en todas las asignaturas que lo tengan
        con_asterisco = Asignatura.objects.filter(name__contains="*")
        n_asterisco = con_asterisco.count()
        if n_asterisco:
            if dry_run:
                self.stdout.write(
                    self.style.NOTICE(
                        f"[dry-run] Se quitaría el asterisco del nombre en {n_asterisco} asignaturas."
                    )
                )
            else:
                to_fix = list(con_asterisco.only("id", "name"))
                for a in to_fix:
                    a.name = a.name.replace("*", "")
                Asignatura.objects.bulk_update(to_fix, ["name"])
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Quitado asterisco del nombre en {n_asterisco} asignaturas."
                    )
                )

        qs = Asignatura.objects.all()
        if only_empty:
            qs = qs.filter(models.Q(palabras_clave__isnull=True) | models.Q(palabras_clave=""))  # type: ignore[name-defined]

        total = qs.count()
        if limit is not None:
            qs = qs[:limit]

        self.stdout.write(
            self.style.NOTICE(
                f"Procesando asignaturas para palabras_clave: total={total}, "
                f"limit={limit}, only_empty={only_empty}, clear={clear}, dry_run={dry_run}"
            )
        )

        if clear and not dry_run:
            qs.update(palabras_clave="")

        updated: List[Asignatura] = []

        for asignatura in qs.iterator():
            original = asignatura.palabras_clave or ""
            computed = build_keywords(asignatura.name or "")

            if dry_run:
                self.stdout.write(
                    f"[dry-run] Asignatura id={asignatura.id} name='{asignatura.name}' "
                    f"-> palabras_clave='{computed}'"
                )
                continue

            # Evitar trabajo innecesario si no cambia
            if original == computed:
                continue

            asignatura.palabras_clave = computed
            updated.append(asignatura)

        if dry_run:
            self.stdout.write(self.style.SUCCESS("Dry-run completado."))
            return

        if not updated:
            self.stdout.write(self.style.SUCCESS("No hay asignaturas a actualizar."))
            return

        # Guardar en bloques para eficiencia
        from django.db import transaction

        batch_size = 500
        with transaction.atomic():
            for i in range(0, len(updated), batch_size):
                Asignatura.objects.bulk_update(
                    updated[i : i + batch_size], ["palabras_clave"]
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Actualizadas {len(updated)} asignaturas con palabras_clave."
            )
        )

