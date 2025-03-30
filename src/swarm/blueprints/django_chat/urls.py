from django.urls import path
from . import views

app_name = "django_chat"

urlpatterns = [
    path('', views.django_chat, name='django_chat'),
]
