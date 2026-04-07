from __future__ import annotations

from typing import List

from rest_framework import generics
from rest_framework.response import Response
from rest_framework.request import Request

from django.db.models import Q

from .models import Titulo, TituloSimilaridad
from .serializers import TituloSerializer, TituloSimilarSerializer


class TituloListAPIView(generics.ListAPIView):
    """
    Endpoint de listado para el buscador (autocompletado).
    Permite filtrar por texto y, si hace falta, por universidad y área.
    """
    serializer_class = TituloSerializer

    def get_queryset(self):
        qs = Titulo.objects.select_related("universidad", "area")
        request: Request = self.request
        # Query params pensados para el frontend:
        # - search: texto que escribe el usuario
        # - universidad_id / area_id: filtros opcionales
        search = request.query_params.get("search")
        universidad_id = request.query_params.get("universidad_id")
        area_id = request.query_params.get("area_id")

        if search:
            qs = qs.filter(name__icontains=search)
        if universidad_id:
            qs = qs.filter(universidad_id=universidad_id)
        if area_id:
            qs = qs.filter(area_id=area_id)

        return qs


class TituloDetailAPIView(generics.RetrieveAPIView):
    """
    Devuelve el detalle de una titulación con su universidad, área y asignaturas.
    Es la llamada que se hace al seleccionar un resultado del buscador.
    """
    # select_related/prefetch_related para evitar consultas extra al devolver relaciones.
    queryset = Titulo.objects.select_related("universidad", "area").prefetch_related(
        "asignatura_set"
    )
    serializer_class = TituloSerializer


class TituloSimilaresAPIView(generics.GenericAPIView):
    """
    Endpoint de recomendación.
    Nota: aquí no calculamos similitud; solo consultamos la tabla precalculada TituloSimilaridad.
    """
    # DRF exige definir queryset o get_queryset aunque usemos una consulta ad hoc
    queryset = TituloSimilaridad.objects.all()
    serializer_class = TituloSimilarSerializer

    def get(self, request: Request, pk: int) -> Response:
        # Validación rápida: si el título no existe, devolvemos 404 controlado.
        try:
            Titulo.objects.get(pk=pk)
        except Titulo.DoesNotExist:
            return Response(
                {"detail": "Título no encontrado."},
                status=404,
            )
        # `limit` evita devolver una lista enorme; si viene mal, usamos 10.
        limit_param = request.query_params.get("limit")
        try:
            limit = int(limit_param) if limit_param is not None else 10
            if limit <= 0:
                limit = 10
        except ValueError:
            limit = 10

        similitudes = (
            TituloSimilaridad.objects.filter(
                Q(titulo_origen_id=pk) | Q(titulo_destino_id=pk)
            )
            .select_related(
                "titulo_origen__universidad",
                "titulo_origen__area",
                "titulo_destino__universidad",
                "titulo_destino__area",
            )
            .order_by("-score")[:limit]
        )
        # Construimos un payload plano (solo los campos que pinta el frontend).
        # Esto simplifica el cliente y evita mandar más datos de los necesarios.
        data: List[dict] = []
        for sim in similitudes:
            # Si el título origen de la fila es el pk, el similar es el destino;
            # si no, el similar es el origen.
            if sim.titulo_origen_id == pk:
                similar = sim.titulo_destino
            else:
                similar = sim.titulo_origen

            if similar.universidad_id and getattr(similar.universidad, "logo", None):
                logo_url = similar.universidad.logo.url
            else:
                logo_url = None

            data.append(
                {
                    "titulo_id": similar.id,
                    "titulo_name": similar.name,
                    "universidad_name": similar.universidad.name
                    if similar.universidad_id
                    else None,
                    "universidad_logo": logo_url,
                    "area_name": similar.area.name if similar.area_id else None,
                    "score": sim.score,
                }
            )

        serializer = self.get_serializer(data, many=True)
        return Response(serializer.data)

