from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AgentInstructionViewSet

router = DefaultRouter()
router.register(r'instructions', AgentInstructionViewSet, basename='instructions')

urlpatterns = [
    path('', include(router.urls)),
]
