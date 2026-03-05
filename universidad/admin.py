from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from .models import Titulo, Asignatura, Related, Area, Universidad


@admin.register(Titulo)
class TituloAdmin(admin.ModelAdmin):
    list_display = ("name", "universidad", "area", "ver_asignaturas")
    list_filter = ("universidad",)
    search_fields = ("name",)

    @admin.display(description="Asignaturas")
    def ver_asignaturas(self, obj):
        url = (
            reverse("admin:universidad_asignatura_changelist")
            + f"?titulo__id__exact={obj.id}"
        )
        return format_html('<a href="{}">Ver asignaturas</a>', url)


@admin.register(Asignatura)
class AsignaturaAdmin(admin.ModelAdmin):
    list_display = ("name", "get_universidad", "titulo")
    search_fields = ("name", "titulo__name")

    @admin.display(description="Universidad")
    def get_universidad(self, obj):
        return obj.titulo.universidad


admin.site.register(Related)
admin.site.register(Area)
admin.site.register(Universidad)
