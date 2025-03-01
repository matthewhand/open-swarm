from django.urls import path
from . import views

app_name = "messenger"

urlpatterns = [
    path('', views.messenger, name='messenger'),
]
