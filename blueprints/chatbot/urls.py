from django.urls import path
from . import views

app_name = "chatbot"

urlpatterns = [
    path('', views.chatbot_view, name='chatbot_view'),
    path('create/', views.create_chat, name='create_chat'),
    path('delete/<str:conversation_id>/', views.delete_chat, name='delete_chat'),
]
