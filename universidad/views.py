from django.shortcuts import render


def buscador(request):
    """
    Página principal de búsqueda de titulaciones y similares.
    """
    return render(request, "universidad/buscador.html")
