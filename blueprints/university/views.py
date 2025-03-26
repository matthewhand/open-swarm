from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.request import Request # Import Request
from drf_spectacular.utils import extend_schema
import os
import logging

from swarm.auth import EnvOrTokenAuthentication

logger = logging.getLogger(__name__)

# Base viewset to handle dynamic permission based on ENABLE_API_AUTH
class UniversityBaseViewSet(ModelViewSet):
    authentication_classes = [EnvOrTokenAuthentication]
    permission_classes = [AllowAny]

    def initial(self, request, *args, **kwargs):
        # Call super().initial() FIRST as per standard DRF practice
        super().initial(request, *args, **kwargs)
        logger.debug(f"After super().initial(), format_kwarg is: {getattr(self, 'format_kwarg', 'Not Set')}")

        # Authentication check
        enable_auth = os.getenv("ENABLE_API_AUTH", "false").lower() in ("true", "1", "t")
        if enable_auth:
            self.perform_authentication(request)
            if not request.user or not request.user.is_authenticated:
                from rest_framework.exceptions import AuthenticationFailed
                raise AuthenticationFailed("Invalid token.")

    def get_permissions(self):
        enable_auth = os.getenv("ENABLE_API_AUTH", "false").lower() in ("true", "1", "t")
        if enable_auth:
            return [IsAuthenticated()]
        return [AllowAny()]

    def get_serializer_context(self):
        """
        Extra context provided to the serializer class.
        Workaround: Explicitly add 'format' key with None if format_kwarg is missing.
        """
        # Get the base context from DRF's implementation
        try:
            context = super().get_serializer_context()
        except AttributeError as e:
             # If super().get_serializer_context() itself fails due to missing format_kwarg
             if 'format_kwarg' in str(e):
                  logger.warning("AttributeError for 'format_kwarg' in super().get_serializer_context(). Providing default context.")
                  context = {
                       'request': self.request,
                       'format': None, # Provide None as fallback
                       'view': self
                  }
             else:
                  raise # Re-raise other AttributeErrors
        except Exception as e:
             logger.error(f"Unexpected error in super().get_serializer_context(): {e}")
             # Provide a minimal context as a fallback
             context = { 'request': self.request, 'format': None, 'view': self }


        # Ensure 'format' key exists, defaulting to None if format_kwarg is missing
        if 'format' not in context:
             context['format'] = getattr(self, 'format_kwarg', None)
             if context['format'] is None:
                   logger.debug("Manually adding 'format: None' to serializer context as format_kwarg was missing.")

        # Ensure other standard keys are present (request, view)
        if 'request' not in context: context['request'] = self.request
        if 'view' not in context: context['view'] = self

        return context

# ... (rest of the viewset definitions remain the same) ...

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
