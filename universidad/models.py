from django.db import models

# Create your models here.
class Universidad(models.Model):
    """Universidad que imparte titulaciones (incluye logo opcional para la interfaz)."""

    name = models.CharField(max_length=250)
    description = models.TextField()
    logo = models.ImageField(
        upload_to="logos_universidades/",
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name_plural = 'Universidades'

    def __str__(self):
        return f"{self.name}" 

class Area(models.Model):
    """Área académica para agrupar titulaciones (incluye empleabilidad estimada)."""

    name = models.CharField(max_length=250)
    empleabilidad = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        null=True,
        blank=True,
        help_text="Porcentaje estimado de empleabilidad (0-100, admite 1 decimal).",
    )

    def __str__(self):
        return f"{self.name}"        

class Titulo(models.Model):
    """Titulación (grado/máster) asociada a una universidad y un área."""

    universidad = models.ForeignKey(Universidad, on_delete=models.CASCADE)
    area = models.ForeignKey(Area, on_delete=models.CASCADE)
    name = models.CharField(max_length=250)
    # El slug se usa sobre todo para deduplicar en importaciones (y facilitar URLs si se necesita).
    slug = models.CharField(max_length=250, null=True, blank=True)
    
    def __str__(self):
        return f"{self.name} ({self.area.name})"

class Asignatura(models.Model):
    """Asignatura perteneciente a una titulación (base para keywords y similitud)."""

    titulo = models.ForeignKey(Titulo, on_delete=models.CASCADE)
    name = models.CharField(max_length=250)
    slug = models.CharField(max_length=250, null=True, blank=True)
    # Texto derivado del nombre (sin acentos/stopwords) usado para calcular similitud entre títulos.
    palabras_clave = models.CharField(max_length=250, null=True, blank=True) 
        
    def __str__(self):
        return f"{self.name}"

class TituloSimilaridad(models.Model):
    """Similitud del coseno entre dos titulaciones (precalculada)."""
    titulo_origen = models.ForeignKey(
        Titulo,
        on_delete=models.CASCADE,
        related_name="similitudes_desde",
    )
    titulo_destino = models.ForeignKey(
        Titulo,
        on_delete=models.CASCADE,
        related_name="similitudes_hacia",
    )
    score = models.FloatField(help_text="Similitud del coseno entre 0 y 1")

    class Meta:
        # Evita duplicar filas para el mismo par (origen, destino).
        constraints = [
            models.UniqueConstraint(
                fields=["titulo_origen", "titulo_destino"],
                name="unique_titulo_similaridad_par",
            )
        ]
        verbose_name = "Similitud entre títulos"
        verbose_name_plural = "Similitudes entre títulos"

    def __str__(self):
        return f"{self.titulo_origen.name} <-> {self.titulo_destino.name} ({self.score:.3f})"