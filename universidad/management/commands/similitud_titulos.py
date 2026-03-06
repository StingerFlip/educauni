"""
Precalcula la similitud del coseno entre titulaciones por grupo de áreas.
Usa palabras_clave de las asignaturas (split por coma) como vectores de conteo.
"""
from __future__ import annotations

import math
from collections import Counter
from typing import Dict, List, Set, Tuple

from django.core.management.base import BaseCommand
from django.db import transaction

from universidad.models import Asignatura, Titulo, TituloSimilaridad


# Grupos de áreas afines: cada Titulo solo se compara con Titulos de su grupo.
AREA_GROUPS: List[Tuple[str, List[int]]] = [
    ("STEM", [2, 3, 5]),  # Ciencias, Ciencias de la Salud, Ingeniería y Arquitectura
    (
        "Derecho, sociales y economía",
        [4, 7, 9, 11],
    ),  # Derecho, Ciencias Políticas, Ciencias Sociales, Economía y Empresa
    ("Artes y humanidades", [1, 10]),  # Artes y Humanidades, Música
    ("Educación", [6]),
]


def get_keywords_for_titulo(titulo: Titulo) -> Counter:
    """Devuelve un Counter de términos (palabras_clave split por coma) de las asignaturas del título."""
    counter: Counter = Counter()
    asignaturas = Asignatura.objects.filter(titulo=titulo).exclude(
        palabras_clave__isnull=True
    ).exclude(palabras_clave="")
    for asig in asignaturas.only("palabras_clave"):
        raw = (asig.palabras_clave or "").strip()
        if not raw:
            continue
        for term in raw.split(","):
            t = term.strip()
            if t:
                counter[t] += 1
    return counter


def build_vocabulary(titulos: List[Titulo]) -> List[str]:
    """Construye el vocabulario (lista ordenada de términos únicos) del grupo."""
    vocab: Set[str] = set()
    for titulo in titulos:
        c = get_keywords_for_titulo(titulo)
        vocab.update(c.keys())
    return sorted(vocab)


def counter_to_vector(counter: Counter, vocabulary: List[str]) -> List[float]:
    """Convierte un Counter a un vector de conteos según el orden del vocabulario."""
    return [float(counter.get(term, 0)) for term in vocabulary]


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Similitud del coseno: (a·b) / (||a|| * ||b||). Devuelve 0 si alguna norma es 0."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class Command(BaseCommand):
    help = (
        "Precalcula la similitud del coseno entre titulaciones por grupo de áreas "
        "y guarda los resultados en TituloSimilaridad."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Vacía TituloSimilaridad antes de recalcular.",
        )
        parser.add_argument(
            "--min-score",
            type=float,
            default=0.1,
            help="Umbral mínimo de similitud para guardar (default: 0.1).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Muestra qué haría sin escribir en la base de datos.",
        )

    def handle(self, *args, **options):
        clear = options["clear"]
        min_score = options["min_score"]
        dry_run = options["dry_run"]

        if not dry_run and clear:
            deleted, _ = TituloSimilaridad.objects.all().delete()
            self.stdout.write(
                self.style.WARNING(f"Eliminadas {deleted} filas de TituloSimilaridad.")
            )

        total_created = 0

        for group_name, area_ids in AREA_GROUPS:
            titulos = list(
                Titulo.objects.filter(area_id__in=area_ids).order_by("id")
            )
            if len(titulos) < 2:
                self.stdout.write(
                    self.style.NOTICE(
                        f"Grupo '{group_name}': {len(titulos)} títulos, se omite."
                    )
                )
                continue

            vocabulary = build_vocabulary(titulos)
            if not vocabulary:
                self.stdout.write(
                    self.style.NOTICE(
                        f"Grupo '{group_name}': vocabulario vacío, se omite."
                    )
                )
                continue

            # Vector por titulo (id -> lista de conteos)
            vectors: Dict[int, List[float]] = {}
            for titulo in titulos:
                counter = get_keywords_for_titulo(titulo)
                vectors[titulo.id] = counter_to_vector(counter, vocabulary)

            # Pares (A, B) con A.id < B.id
            to_create: List[TituloSimilaridad] = []
            for i in range(len(titulos)):
                for j in range(i + 1, len(titulos)):
                    t_a, t_b = titulos[i], titulos[j]
                    score = cosine_similarity(vectors[t_a.id], vectors[t_b.id])
                    if score < min_score:
                        continue
                    if dry_run:
                        self.stdout.write(
                            f"  [dry-run] {t_a.name} <-> {t_b.name} = {score:.4f}"
                        )
                        total_created += 1
                        continue
                    to_create.append(
                        TituloSimilaridad(
                            titulo_origen=t_a,
                            titulo_destino=t_b,
                            score=round(score, 6),
                        )
                    )

            if not dry_run and to_create:
                with transaction.atomic():
                    TituloSimilaridad.objects.bulk_create(to_create)
                total_created += len(to_create)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Grupo '{group_name}': {len(to_create)} similitudes guardadas."
                    )
                )

        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Dry-run: se habrían creado {total_created} similitudes."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Total similitudes en BD: {TituloSimilaridad.objects.count()}."
                )
            )
