from __future__ import annotations

from rest_framework import serializers

from .models import Universidad, Area, Titulo, Asignatura


class UniversidadMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Universidad
        fields = ["id", "name", "logo"]


class AreaMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Area
        fields = ["id", "name", "empleabilidad"]


class AsignaturaMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asignatura
        fields = ["id", "name"]


class TituloSerializer(serializers.ModelSerializer):
    universidad = UniversidadMiniSerializer(read_only=True)
    area = AreaMiniSerializer(read_only=True)
    asignaturas = AsignaturaMiniSerializer(
        source="asignatura_set", many=True, read_only=True
    )

    class Meta:
        model = Titulo
        fields = ["id", "name", "slug", "universidad", "area", "asignaturas"]


class TituloSimilarSerializer(serializers.Serializer):
    titulo_id = serializers.IntegerField()
    titulo_name = serializers.CharField()
    universidad_name = serializers.CharField(allow_null=True)
    universidad_logo = serializers.CharField(allow_null=True)
    area_name = serializers.CharField(allow_null=True)
    score = serializers.FloatField()

