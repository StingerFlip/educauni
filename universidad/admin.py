from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.text import Truncator

from .models import Titulo, Asignatura, Area, Universidad, TituloSimilaridad


@admin.register(Titulo)
class TituloAdmin(admin.ModelAdmin):
    list_display = ("name", "universidad", "area", "ver_asignaturas")
    list_filter = ("universidad",)
    search_fields = ("name",)

    @admin.display(description="Asignaturas")
    def ver_asignaturas(self, obj):
        # Enlace directo al listado de asignaturas ya filtrado por este título.
        url = (
            reverse("admin:universidad_asignatura_changelist")
            + f"?titulo__id__exact={obj.id}"
        )
        return format_html('<a href="{}">Ver asignaturas</a>', url)


@admin.register(Asignatura)
class AsignaturaAdmin(admin.ModelAdmin):
    list_display = ("name", "get_universidad", "titulo")
    list_filter = ("titulo__universidad", "titulo__area")
    search_fields = ("name", "titulo__name")

    @admin.display(description="Universidad")
    def get_universidad(self, obj):
        return obj.titulo.universidad


@admin.register(TituloSimilaridad)
class TituloSimilaridadAdmin(admin.ModelAdmin):
    list_display = ("excerpt_origen", "excerpt_destino", "score")
    list_filter = ("titulo_origen__area",)
    search_fields = ("titulo_origen__name", "titulo_destino__name")
    ordering = ("-score",)

    @admin.display(description="Título origen")
    def excerpt_origen(self, obj):
        # Recortamos nombres largos para que el listado sea legible.
        if obj.titulo_origen_id is None:
            return "—"
        return Truncator(obj.titulo_origen.name).chars(50, truncate="…")

    @admin.display(description="Título destino")
    def excerpt_destino(self, obj):
        # Recortamos nombres largos para que el listado sea legible.
        if obj.titulo_destino_id is None:
            return "—"
        return Truncator(obj.titulo_destino.name).chars(50, truncate="…")


admin.site.register(Area)
admin.site.register(Universidad)
