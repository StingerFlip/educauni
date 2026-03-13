from __future__ import annotations

from django.urls import path

from .api_views import (
    TituloListAPIView,
    TituloDetailAPIView,
    TituloSimilaresAPIView,
)
from .views import buscador


urlpatterns = [
    # Frontend sencillo con Django + JS vanilla
    path("", buscador, name="buscador"),
    # API REST
    path("api/titulos/", TituloListAPIView.as_view(), name="api_titulo_list"),
    path("api/titulos/<int:pk>/", TituloDetailAPIView.as_view(), name="api_titulo_detail"),
    path(
        "api/titulos/<int:pk>/similares/",
        TituloSimilaresAPIView.as_view(),
        name="api_titulo_similares",
    ),
]

