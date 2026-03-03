from django.db import models

# Create your models here.
class Universidad(models.Model):
    name = models.CharField(max_length=250)
    description = models.TextField()

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
    
    def __str__(self):
        return f"{self.name} ({self.area.name})"

class Asignatura(models.Model):
    titulo = models.ForeignKey(Titulo, on_delete=models.CASCADE)
    name = models.CharField(max_length=250)
        
    def __str__(self):
        return f"{self.name}"

class Related(models.Model):
    asignatura = models.ForeignKey(Asignatura, on_delete=models.CASCADE, related_name='asignatura')
    relacion = models.ForeignKey(Asignatura, on_delete=models.CASCADE, related_name='relacion')
    value = models.DecimalField(max_digits=10, decimal_places=8, default=0.0)

    def __str__(self):
        return f"{self.asignatura.name} - {self.relacion.name}"

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False