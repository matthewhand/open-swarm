import pytest
import os
import sys
import types
from django.test import Client, override_settings # Need override_settings for ROOT_URLCONF
from django.urls import path, include, clear_url_caches, set_urlconf
from django.conf import settings
# from django.core.management import call_command # Not needed

# Set environment variables BEFORE Django setup
os.environ["UNIT_TESTING"] = "true"
os.environ["ENABLE_API_AUTH"] = "false"
os.environ["SWARM_BLUEPRINTS"] = "university" # Required by conftest/settings

# Ensure Django is setup (conftest should handle this)
if not settings.configured:
     import django
     django.setup()

# No INSTALLED_APPS override needed

# Create a dynamic module for the test URLconf
test_urlconf_name = __name__ + '.temp_urls_create_retrieve'
try:
    from blueprints.university import urls as university_urls
    from swarm import urls as swarm_urls
    core_patterns = [p for p in swarm_urls.urlpatterns if not str(getattr(p, 'pattern','')).startswith('v1/university/')]
    test_urlpatterns = core_patterns + [path('v1/university/', include((university_urls, 'university')))]
    temp_urls_module = types.ModuleType(__name__ + '.temp_urls_create_retrieve')
    temp_urls_module.urlpatterns = test_urlpatterns
    sys.modules[test_urlconf_name] = temp_urls_module
    print(f"Created temporary URLconf module: {test_urlconf_name}")
except ImportError:
    print("ERROR: Cannot import university URLs for test setup.")
    test_urlconf_name = settings.ROOT_URLCONF
except Exception as e:
    print(f"ERROR creating temp URLconf: {e}")
    test_urlconf_name = settings.ROOT_URLCONF

# Define the override settings decorator common to all tests in this module
# Only override ROOT_URLCONF
override_decorator = override_settings(
    ROOT_URLCONF=test_urlconf_name
    # INSTALLED_APPS=... # REMOVED
)

# Use database marker for the module
pytestmark = pytest.mark.django_db(transaction=True)

@pytest.fixture(scope="function", autouse=True)
def bypass_auth():
    from blueprints.university.views import UniversityBaseViewSet
    original_initial = UniversityBaseViewSet.initial
    def mock_initial(self, request, *args, **kwargs):
        request.user = type('User', (), {'is_authenticated': True, 'is_anonymous': False})()
    UniversityBaseViewSet.initial = mock_initial
    yield
    UniversityBaseViewSet.initial = original_initial

@pytest.fixture(scope="module", autouse=True)
def manage_test_environment_module():
    """Set up URLconf once for the module."""
    original_urlconf = getattr(settings, 'ROOT_URLCONF', None) # Store original safely
    # Set the URLconf *before* tests run, override_decorator will handle it per-test too
    set_urlconf(test_urlconf_name)
    clear_url_caches()
    print(f"Module Setup: Set URLConf to {test_urlconf_name}")

    # Migrations should be handled by pytest-django now

    yield # Tests run here

    # Teardown
    if original_urlconf:
        set_urlconf(original_urlconf)
    else:
        set_urlconf(None)
    clear_url_caches()
    if test_urlconf_name in sys.modules: del sys.modules[test_urlconf_name]
    print(f"Module Teardown: Cleaned up URLConf {test_urlconf_name}")


# Apply override_settings (which only overrides ROOT_URLCONF now)
@override_decorator
def test_create_and_retrieve_teaching_unit(client):
    data = { "code": "TU001", "name": "Test Teaching Unit", "teaching_prompt": "Prompt text" }
    response = client.post("/v1/university/teaching-units/", data, content_type="application/json")
    assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.content.decode()}"
    tu_id = response.json()["id"]
    response = client.get(f"/v1/university/teaching-units/{tu_id}/")
    assert response.status_code == 200
    assert response.json()["code"] == "TU001"

@override_decorator
def test_create_and_retrieve_topic(client):
    # Need TeachingUnit first
    tu_data = {"code": "TU002", "name": "For Topic", "teaching_prompt": "TP"}
    res_tu = client.post("/v1/university/teaching-units/", tu_data, content_type="application/json")
    assert res_tu.status_code == 201, f"Prereq TU failed: {res_tu.content.decode()}"
    tu_id = res_tu.json()["id"]

    data = { "teaching_unit": tu_id, "name": "Test Topic", "teaching_prompt": "Topic prompt" }
    response = client.post("/v1/university/topics/", data, content_type="application/json")
    assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.content.decode()}"
    topic_id = response.json()["id"]
    response = client.get(f"/v1/university/topics/{topic_id}/")
    assert response.status_code == 200
    assert response.json()["name"] == "Test Topic"

@override_decorator
def test_create_and_retrieve_learning_objective(client):
    # Need TeachingUnit and Topic first
    tu_data = {"code": "TU003", "name": "For LO", "teaching_prompt": "TP"}
    res_tu = client.post("/v1/university/teaching-units/", tu_data, content_type="application/json")
    assert res_tu.status_code == 201, f"Prereq TU failed: {res_tu.content.decode()}"
    tu_id = res_tu.json()["id"]
    topic_data = {"teaching_unit": tu_id, "name": "Topic for LO", "teaching_prompt": "TP"}
    res_topic = client.post("/v1/university/topics/", topic_data, content_type="application/json")
    assert res_topic.status_code == 201, f"Prereq Topic failed: {res_topic.content.decode()}"
    topic_id = res_topic.json()["id"]

    data = {"topic": topic_id, "description": "Objective description"}
    response = client.post("/v1/university/learning-objectives/", data, content_type="application/json")
    assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.content.decode()}"
    lo_id = response.json()["id"]
    response = client.get(f"/v1/university/learning-objectives/{lo_id}/")
    assert response.status_code == 200
    assert "Objective description" in response.json()["description"]

@override_decorator
def test_create_and_retrieve_subtopic(client):
     # Need TeachingUnit and Topic first
    tu_data = {"code": "TU004", "name": "For Subtopic", "teaching_prompt": "TP"}
    res_tu = client.post("/v1/university/teaching-units/", tu_data, content_type="application/json")
    assert res_tu.status_code == 201, f"Prereq TU failed: {res_tu.content.decode()}"
    tu_id = res_tu.json()["id"]
    topic_data = {"teaching_unit": tu_id, "name": "Topic for Subtopic", "teaching_prompt": "TP"}
    res_topic = client.post("/v1/university/topics/", topic_data, content_type="application/json")
    assert res_topic.status_code == 201, f"Prereq Topic failed: {res_topic.content.decode()}"
    topic_id = res_topic.json()["id"]

    data = {"topic": topic_id, "name": "Test Subtopic", "teaching_prompt": "Subtopic prompt"}
    response = client.post("/v1/university/subtopics/", data, content_type="application/json")
    assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.content.decode()}"
    subtopic_id = response.json()["id"]
    response = client.get(f"/v1/university/subtopics/{subtopic_id}/")
    assert response.status_code == 200
    assert response.json()["name"] == "Test Subtopic"

@override_decorator
def test_create_and_retrieve_course(client):
     # Need TeachingUnit first
    tu_data = {"code": "TU005", "name": "For Course", "teaching_prompt": "TP"}
    res_tu = client.post("/v1/university/teaching-units/", tu_data, content_type="application/json")
    assert res_tu.status_code == 201, f"Prereq TU failed: {res_tu.content.decode()}"
    tu_id = res_tu.json()["id"]

    data = { "name": "Test Course", "code": "TC001", "coordinator": "Coordinator Name", "teaching_prompt": "Course prompt", "teaching_units": [tu_id] }
    response = client.post("/v1/university/courses/", data, content_type="application/json")
    assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.content.decode()}"
    course_id = response.json()["id"]
    response = client.get(f"/v1/university/courses/{course_id}/")
    assert response.status_code == 200
    assert response.json()["code"] == "TC001"

@override_decorator
def test_create_and_retrieve_student(client):
    data = {"name": "Test Student", "gpa": "3.50", "status": "active"}
    response = client.post("/v1/university/students/", data, content_type="application/json")
    assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.content.decode()}"
    student_id = response.json()["id"]
    response = client.get(f"/v1/university/students/{student_id}/")
    assert response.status_code == 200
    assert response.json()["name"] == "Test Student"

@override_decorator
def test_create_and_retrieve_enrollment(client):
    # Need TeachingUnit and Student first
    tu_data = {"code": "TU006", "name": "For Enrollment", "teaching_prompt": "TP"}
    res_tu = client.post("/v1/university/teaching-units/", tu_data, content_type="application/json")
    assert res_tu.status_code == 201, f"Prereq TU failed: {res_tu.content.decode()}"
    tu_id = res_tu.json()["id"]
    student_data = {"name": "Enrollment Student", "gpa": "3.75", "status": "active"}
    res_student = client.post("/v1/university/students/", student_data, content_type="application/json")
    assert res_student.status_code == 201, f"Prereq Student failed: {res_student.content.decode()}"
    student_id = res_student.json()["id"]

    data = {"student": student_id, "teaching_unit": tu_id, "status": "enrolled"}
    response = client.post("/v1/university/enrollments/", data, content_type="application/json")
    assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.content.decode()}"
    enrollment_id = response.json()["id"]
    response = client.get(f"/v1/university/enrollments/{enrollment_id}/")
    assert response.status_code == 200
    retrieved = response.json()
    assert retrieved.get("teaching_unit") == tu_id

@override_decorator
def test_create_and_retrieve_assessment_item(client):
     # Need TeachingUnit, Student, Enrollment first
    tu_data = {"code": "TU007", "name": "For Assessment", "teaching_prompt": "TP"}
    res_tu = client.post("/v1/university/teaching-units/", tu_data, content_type="application/json")
    assert res_tu.status_code == 201, f"Prereq TU failed: {res_tu.content.decode()}"
    tu_id = res_tu.json()["id"]
    student_data = {"name": "Assessment Student", "gpa": "4.00", "status": "active"}
    res_student = client.post("/v1/university/students/", student_data, content_type="application/json")
    assert res_student.status_code == 201, f"Prereq Student failed: {res_student.content.decode()}"
    student_id = res_student.json()["id"]
    enrollment_data = {"student": student_id, "teaching_unit": tu_id, "status": "enrolled"}
    res_enroll = client.post("/v1/university/enrollments/", enrollment_data, content_type="application/json")
    assert res_enroll.status_code == 201, f"Prereq Enrollment failed: {res_enroll.content.decode()}"
    enrollment_id = res_enroll.json()["id"]

    data = { "enrollment": enrollment_id, "title": "Test Assessment", "status": "pending", "due_date": "2025-12-31T23:59:59Z", "weight": "20.00" }
    response = client.post("/v1/university/assessment-items/", data, content_type="application/json")
    assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.content.decode()}"
    assessment_id = response.json()["id"]
    response = client.get(f"/v1/university/assessment-items/{assessment_id}/")
    assert response.status_code == 200
    assert response.json()["title"] == "Test Assessment"
