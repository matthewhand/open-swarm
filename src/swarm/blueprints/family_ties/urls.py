from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AgentInstructionViewSet

router = DefaultRouter()
router.register(r'instructions', AgentInstructionViewSet, basename='instructions')

urlpatterns = [
    path('', include(router.urls)),
]
