from django.shortcuts import render


def buscador(request):
    """
    Página principal de búsqueda de titulaciones y similares.
    """
    # La lógica de datos vive en la API; aquí solo servimos la plantilla del frontend.
    return render(request, "universidad/buscador.html")
