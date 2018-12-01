from django.urls import path
from .views import ScrapperView


urlpatterns = [
    path("", ScrapperView.as_view(), name="scrapper", )
]