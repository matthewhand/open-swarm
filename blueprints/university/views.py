from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated, AllowAny
from drf_spectacular.utils import extend_schema
import os

from swarm.auth import EnvOrTokenAuthentication

# Base viewset to handle dynamic permission based on ENABLE_API_AUTH
class UniversityBaseViewSet(ModelViewSet):
    authentication_classes = [EnvOrTokenAuthentication]
    permission_classes = [AllowAny]

    def initial(self, request, *args, **kwargs):
        # Only enforce authentication if ENABLE_API_AUTH is enabled
        enable_auth = os.getenv("ENABLE_API_AUTH", "false").lower() in ("true", "1", "t")
        if enable_auth:
            self.perform_authentication(request)
            if not request.user or not request.user.is_authenticated:
                from rest_framework.exceptions import AuthenticationFailed
                raise AuthenticationFailed("Invalid token.")
        super().initial(request, *args, **kwargs)

    def get_permissions(self):
        enable_auth = os.getenv("ENABLE_API_AUTH", "false").lower() in ("true", "1", "t")
        if enable_auth:
            return [IsAuthenticated()]
        return [AllowAny()]

# Import models from the university blueprint
from blueprints.university.models import (
    TeachingUnit,
    Topic,
    LearningObjective,
    Subtopic,
    Course,
    Student,
    Enrollment,
    AssessmentItem,
    filter_students
)
# Import serializers from the university blueprint serializers module
from blueprints.university.serializers import (
    TeachingUnitSerializer,
    TopicSerializer,
    LearningObjectiveSerializer,
    SubtopicSerializer,
    CourseSerializer,
    StudentSerializer,
    EnrollmentSerializer,
    AssessmentItemSerializer
)

class TeachingUnitViewSet(UniversityBaseViewSet):
    queryset = TeachingUnit.objects.all()
    serializer_class = TeachingUnitSerializer

class TopicViewSet(UniversityBaseViewSet):
    queryset = Topic.objects.all()
    serializer_class = TopicSerializer

class LearningObjectiveViewSet(UniversityBaseViewSet):
    queryset = LearningObjective.objects.all()
    serializer_class = LearningObjectiveSerializer

class SubtopicViewSet(UniversityBaseViewSet):
    queryset = Subtopic.objects.all()
    serializer_class = SubtopicSerializer

class CourseViewSet(UniversityBaseViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer

class StudentViewSet(UniversityBaseViewSet):
    queryset = Student.objects.all()
    serializer_class = StudentSerializer

    def get_queryset(self):
        name = self.request.query_params.get("name")
        status = self.request.query_params.get("status")
        unit_codes = self.request.query_params.get("unit_codes")
        if unit_codes:
            unit_codes = unit_codes.split(',')
        if name or status or unit_codes:
            return filter_students(name=name, status=status, unit_codes=unit_codes)
        return super().get_queryset()

class EnrollmentViewSet(UniversityBaseViewSet):
    queryset = Enrollment.objects.all()
    serializer_class = EnrollmentSerializer

class AssessmentItemViewSet(UniversityBaseViewSet):
    queryset = AssessmentItem.objects.all()
    serializer_class = AssessmentItemSerializer

__all__ = [
    "TeachingUnitViewSet",
    "TopicViewSet",
    "LearningObjectiveViewSet",
    "SubtopicViewSet",
    "CourseViewSet",
    "StudentViewSet",
    "EnrollmentViewSet",
    "AssessmentItemViewSet"
]
