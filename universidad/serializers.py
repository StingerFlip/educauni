from __future__ import annotations

from rest_framework import serializers

from .models import Universidad, Area, Titulo, Asignatura


class UniversidadMiniSerializer(serializers.ModelSerializer):
    """Versión compacta de Universidad para respuestas del buscador/detalle."""

    class Meta:
        model = Universidad
        fields = ["id", "name", "logo"]


class AreaMiniSerializer(serializers.ModelSerializer):
    """Versión compacta de Área (incluye empleabilidad) para el detalle."""

    class Meta:
        model = Area
        fields = ["id", "name", "empleabilidad"]


class AsignaturaMiniSerializer(serializers.ModelSerializer):
    """Asignatura en formato simple para listar en el detalle del título."""

    class Meta:
        model = Asignatura
        fields = ["id", "name"]


class TituloSerializer(serializers.ModelSerializer):
    """
    Serializer principal de Título.
    Incluye universidad, área y un listado de asignaturas para que el frontend pueda pintar el detalle.
    """

    universidad = UniversidadMiniSerializer(read_only=True)
    area = AreaMiniSerializer(read_only=True)
    # Usamos `asignatura_set` porque Asignatura apunta a Titulo con ForeignKey.
    asignaturas = AsignaturaMiniSerializer(
        source="asignatura_set", many=True, read_only=True
    )

    class Meta:
        model = Titulo
        fields = ["id", "name", "slug", "universidad", "area", "asignaturas"]


class TituloSimilarSerializer(serializers.Serializer):
    """
    Respuesta plana para la sección de "similares".
    No es ModelSerializer porque la API construye el payload manualmente (campos + score).
    """

    titulo_id = serializers.IntegerField()
    titulo_name = serializers.CharField()
    universidad_name = serializers.CharField(allow_null=True)
    universidad_logo = serializers.CharField(allow_null=True)
    area_name = serializers.CharField(allow_null=True)
    score = serializers.FloatField()

