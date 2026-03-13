from __future__ import annotations

from rest_framework import serializers

from .models import Universidad, Area, Titulo, Asignatura


class UniversidadMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Universidad
        fields = ["id", "name"]


class AreaMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Area
        fields = ["id", "name"]


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
    area_name = serializers.CharField(allow_null=True)
    score = serializers.FloatField()
    score_label = serializers.SerializerMethodField()

    def get_score_label(self, obj):
        # obj puede ser dict u objeto con atributo score
        score = obj.get("score") if isinstance(obj, dict) else getattr(obj, "score", 0.0)
        if score >= 0.7:
            return "alta"
        if score >= 0.4:
            return "media"
        return "baja"

