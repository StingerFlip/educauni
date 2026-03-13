from django.db import models

# Create your models here.
class Universidad(models.Model):
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
    name = models.CharField(max_length=250)

    def __str__(self):
        return f"{self.name}"        

class Titulo(models.Model):
    universidad = models.ForeignKey(Universidad, on_delete=models.CASCADE)
    area = models.ForeignKey(Area, on_delete=models.CASCADE)
    name = models.CharField(max_length=250)
    slug = models.CharField(max_length=250, null=True, blank=True)
    
    def __str__(self):
        return f"{self.name} ({self.area.name})"

class Asignatura(models.Model):
    titulo = models.ForeignKey(Titulo, on_delete=models.CASCADE)
    name = models.CharField(max_length=250)
    slug = models.CharField(max_length=250, null=True, blank=True)
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