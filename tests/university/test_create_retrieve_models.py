import pytest
import os
from django.test import Client
from blueprints.university.blueprint_university import UniversitySupportBlueprint
from unittest.mock import patch

# Set environment variables for consistent test setup
os.environ["UNIT_TESTING"] = "true"
os.environ["SQLITE_DB_PATH"] = f"/tmp/test_db_{os.urandom(8).hex()}.sqlite3"
os.environ["ENABLE_API_AUTH"] = "false"
os.environ["SWARM_BLUEPRINTS"] = "university"  # Limit to university blueprint

# Patch UniversityBaseViewSet.initial to skip authentication enforcement
@pytest.fixture(scope="module")
def bypass_auth():
    from blueprints.university.views import UniversityBaseViewSet
    original_initial = UniversityBaseViewSet.initial
    def mock_initial(self, request, *args, **kwargs):
        request.user = type('User', (), {'is_authenticated': True, 'is_anonymous': False})()
        super(UniversityBaseViewSet, self).initial(request, *args, **kwargs)
    UniversityBaseViewSet.initial = mock_initial
    yield
    UniversityBaseViewSet.initial = original_initial

# Ensure blueprint URLs are registered before tests run
@pytest.fixture(scope="module", autouse=True)
def setup_blueprint_urls(bypass_auth):
    dummy_config = {
        "llm": {
            "default": {
                "provider": "openai",
                "model": "gpt-4o",
                "base_url": "https://api.openai.com/v1",
                "api_key": "dummy"
            }
        }
    }
    blueprint = UniversitySupportBlueprint(config=dummy_config)
    blueprint.register_blueprint_urls()
    yield
    os.environ.pop("SWARM_BLUEPRINTS", None)
    if os.path.exists(os.environ["SQLITE_DB_PATH"]):
        os.remove(os.environ["SQLITE_DB_PATH"])

@pytest.mark.django_db
def test_create_and_retrieve_teaching_unit():
    client = Client()
    data = {
        "code": "TU001",
        "name": "Test Teaching Unit",
        "teaching_prompt": "Prompt text"
    }
    response = client.post("/v1/university/teaching-units/", data, content_type="application/json")
    assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.content}"
    tu = response.json()
    tu_id = tu["id"]
    response = client.get(f"/v1/university/teaching-units/{tu_id}/")
    assert response.status_code == 200
    assert response.json()["code"] == "TU001"

@pytest.mark.django_db
def test_create_and_retrieve_topic():
    client = Client()
    tu_data = {"code": "TU002", "name": "For Topic", "teaching_prompt": "TP"}
    response = client.post("/v1/university/teaching-units/", tu_data, content_type="application/json")
    assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.content}"
    tu_id = response.json()["id"]
    data = {
        "teaching_unit": tu_id,
        "name": "Test Topic",
        "teaching_prompt": "Topic prompt"
    }
    response = client.post("/v1/university/topics/", data, content_type="application/json")
    assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.content}"
    topic_id = response.json()["id"]
    response = client.get(f"/v1/university/topics/{topic_id}/")
    assert response.status_code == 200
    assert response.json()["name"] == "Test Topic"

@pytest.mark.django_db
def test_create_and_retrieve_learning_objective():
    client = Client()
    tu_data = {"code": "TU003", "name": "For LO", "teaching_prompt": "TP"}
    res = client.post("/v1/university/teaching-units/", tu_data, content_type="application/json")
    assert res.status_code == 201, f"Expected 201, got {res.status_code}: {res.content}"
    tu_id = res.json()["id"]
    topic_data = {"teaching_unit": tu_id, "name": "Topic for LO", "teaching_prompt": "TP"}
    res = client.post("/v1/university/topics/", topic_data, content_type="application/json")
    assert res.status_code == 201, f"Expected 201, got {res.status_code}: {res.content}"
    topic_id = res.json()["id"]
    data = {"topic": topic_id, "description": "Objective description"}
    response = client.post("/v1/university/learning-objectives/", data, content_type="application/json")
    assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.content}"
    lo_id = response.json()["id"]
    response = client.get(f"/v1/university/learning-objectives/{lo_id}/")
    assert response.status_code == 200
    assert "Objective description" in response.json()["description"]

@pytest.mark.django_db
def test_create_and_retrieve_subtopic():
    client = Client()
    tu_data = {"code": "TU004", "name": "For Subtopic", "teaching_prompt": "TP"}
    res = client.post("/v1/university/teaching-units/", tu_data, content_type="application/json")
    assert res.status_code == 201, f"Expected 201, got {res.status_code}: {res.content}"
    tu_id = res.json()["id"]
    topic_data = {"teaching_unit": tu_id, "name": "Topic for Subtopic", "teaching_prompt": "TP"}
    res = client.post("/v1/university/topics/", topic_data, content_type="application/json")
    assert res.status_code == 201, f"Expected 201, got {res.status_code}: {res.content}"
    topic_id = res.json()["id"]
    data = {"topic": topic_id, "name": "Test Subtopic", "teaching_prompt": "Subtopic prompt"}
    response = client.post("/v1/university/subtopics/", data, content_type="application/json")
    assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.content}"
    subtopic_id = response.json()["id"]
    response = client.get(f"/v1/university/subtopics/{subtopic_id}/")
    assert response.status_code == 200
    assert response.json()["name"] == "Test Subtopic"

@pytest.mark.django_db
def test_create_and_retrieve_course():
    client = Client()
    tu_data = {"code": "TU005", "name": "For Course", "teaching_prompt": "TP"}
    res = client.post("/v1/university/teaching-units/", tu_data, content_type="application/json")
    assert res.status_code == 201, f"Expected 201, got {res.status_code}: {res.content}"
    tu_id = res.json()["id"]
    data = {
        "name": "Test Course",
        "code": "TC001",
        "coordinator": "Coordinator Name",
        "teaching_prompt": "Course prompt",
        "teaching_units": [tu_id]
    }
    response = client.post("/v1/university/courses/", data, content_type="application/json")
    assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.content}"
    course_id = response.json()["id"]
    response = client.get(f"/v1/university/courses/{course_id}/")
    assert response.status_code == 200
    assert response.json()["code"] == "TC001"

@pytest.mark.django_db
def test_create_and_retrieve_student():
    client = Client()
    data = {"name": "Test Student", "gpa": "3.50", "status": "active"}
    response = client.post("/v1/university/students/", data, content_type="application/json")
    assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.content}"
    student_id = response.json()["id"]
    response = client.get(f"/v1/university/students/{student_id}/")
    assert response.status_code == 200
    assert response.json()["name"] == "Test Student"

@pytest.mark.django_db
def test_create_and_retrieve_enrollment():
    client = Client()
    tu_data = {"code": "TU006", "name": "For Enrollment", "teaching_prompt": "TP"}
    res = client.post("/v1/university/teaching-units/", tu_data, content_type="application/json")
    assert res.status_code == 201, f"Expected 201, got {res.status_code}: {res.content}"
    tu_id = res.json()["id"]
    student_data = {"name": "Enrollment Student", "gpa": "3.75", "status": "active"}
    res = client.post("/v1/university/students/", student_data, content_type="application/json")
    assert res.status_code == 201, f"Expected 201, got {res.status_code}: {res.content}"
    student_id = res.json()["id"]
    data = {"student": student_id, "teaching_unit": tu_id, "status": "enrolled"}
    response = client.post("/v1/university/enrollments/", data, content_type="application/json")
    assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.content}"
    enrollment_id = response.json()["id"]
    response = client.get(f"/v1/university/enrollments/{enrollment_id}/")
    assert response.status_code == 200
    retrieved = response.json()
    assert retrieved.get("teaching_unit") == tu_id

@pytest.mark.django_db
def test_create_and_retrieve_assessment_item():
    client = Client()
    tu_data = {"code": "TU007", "name": "For Assessment", "teaching_prompt": "TP"}
    res = client.post("/v1/university/teaching-units/", tu_data, content_type="application/json")
    assert res.status_code == 201, f"Expected 201, got {res.status_code}: {res.content}"
    tu_id = res.json()["id"]
    student_data = {"name": "Assessment Student", "gpa": "4.00", "status": "active"}
    res = client.post("/v1/university/students/", student_data, content_type="application/json")
    assert res.status_code == 201, f"Expected 201, got {res.status_code}: {res.content}"
    student_id = res.json()["id"]
    enrollment_data = {"student": student_id, "teaching_unit": tu_id, "status": "enrolled"}
    res = client.post("/v1/university/enrollments/", enrollment_data, content_type="application/json")
    assert res.status_code == 201, f"Expected 201, got {res.status_code}: {res.content}"
    enrollment_id = res.json()["id"]
    data = {
        "enrollment": enrollment_id,
        "title": "Test Assessment",
        "status": "pending",
        "due_date": "2025-12-31T23:59:59Z",
        "weight": "20.00"
    }
    response = client.post("/v1/university/assessment-items/", data, content_type="application/json")
    assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.content}"
    assessment_id = response.json()["id"]
    response = client.get(f"/v1/university/assessment-items/{assessment_id}/")
    assert response.status_code == 200
    assert response.json()["title"] == "Test Assessment"
