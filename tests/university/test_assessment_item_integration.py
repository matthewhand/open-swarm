import os
# Set env vars before Django imports
os.environ.setdefault('ENABLE_API_AUTH', 'false')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'swarm.settings')
os.environ.setdefault('SQLITE_DB_PATH', f"/tmp/test_db_{os.urandom(8).hex()}.sqlite3")
os.environ["SWARM_BLUEPRINTS"] = "university"

import django
import sys
import types
import pytest # Import pytest
from django.conf import settings
if not settings.configured:
     django.setup()

# --- Imports after setup ---
import tempfile
import importlib
from django.test import Client, override_settings # Keep override_settings
from django.urls import path, include, clear_url_caches, set_urlconf, get_resolver
from unittest.mock import patch
from blueprints.university.blueprint_university import UniversitySupportBlueprint

# Define the required INSTALLED_APPS for these tests
try:
    from swarm.settings import INSTALLED_APPS as BASE_INSTALLED_APPS_LIST
    BASE_INSTALLED_APPS = tuple(BASE_INSTALLED_APPS_LIST) if isinstance(BASE_INSTALLED_APPS_LIST, list) else BASE_INSTALLED_APPS_LIST
    BASE_INSTALLED_APPS = tuple(app for app in BASE_INSTALLED_APPS if app != 'blueprints.university')
except (ImportError, AttributeError):
    BASE_INSTALLED_APPS = (
        'django.contrib.admin','django.contrib.auth','django.contrib.contenttypes',
        'django.contrib.sessions','django.contrib.messages','django.contrib.staticfiles',
        'rest_framework','rest_framework.authtoken','drf_spectacular','swarm.apps.SwarmConfig',
    )
UNIVERSITY_TEST_APPS = BASE_INSTALLED_APPS + ('blueprints.university',)

# --- Pytest Fixtures ---

# Create a dynamic module for the test URLconf (module scope)
@pytest.fixture(scope="module", autouse=True)
def temp_urlconf_module():
    test_urlconf_name = __name__ + '.temp_urls_assessment_pytest'
    try:
        from blueprints.university import urls as university_urls
        from swarm import urls as swarm_urls
        core_patterns = [p for p in swarm_urls.urlpatterns if not str(getattr(p, 'pattern','')).startswith('v1/university/')]
        test_urlpatterns = core_patterns + [path('v1/university/', include((university_urls, 'university')))]
        temp_module = types.ModuleType(test_urlconf_name)
        temp_module.urlpatterns = test_urlpatterns
        sys.modules[test_urlconf_name] = temp_module
        print(f"Created temporary URLconf module: {test_urlconf_name}")
        yield test_urlconf_name # Provide the name to override_settings
    finally:
        # Teardown: remove module and clear caches
        if test_urlconf_name in sys.modules:
            del sys.modules[test_urlconf_name]
        clear_url_caches()
        print(f"Cleaned up temporary URLconf module: {test_urlconf_name}")

# Fixture to apply override_settings using the dynamic URLconf name
@pytest.fixture(scope="function") # Function scope to reset settings per test
def override_test_settings(temp_urlconf_module):
    with override_settings(ROOT_URLCONF=temp_urlconf_module, INSTALLED_APPS=UNIVERSITY_TEST_APPS):
        # Need to clear caches *after* settings are overridden for the test
        clear_url_caches()
        # Reload URLs based on overridden settings if necessary, though set_urlconf might handle it
        # set_urlconf(temp_urlconf_module) # Re-set just in case
        print(f"Applied override_settings for test: ROOT_URLCONF={temp_urlconf_module}")
        yield
        # Teardown happens automatically when exiting 'with' block
        clear_url_caches()
        # Revert to original ROOT_URLCONF if needed, though override_settings should handle it
        # set_urlconf(settings.ROOT_URLCONF)
        print("Reverted override_settings after test.")


# Use database marker for the class
@pytest.mark.django_db(transaction=True)
class TestAssessmentItemIntegrationPytest: # Renamed class

    @pytest.fixture(autouse=True) # Apply to all methods in this class
    def setup_method(self, client, override_test_settings): # Use client fixture, apply settings override
        """Setup using pytest fixtures."""
        self.client = client # Use the client provided by pytest-django

        # Patch authentication
        from blueprints.university.views import UniversityBaseViewSet
        self.auth_patch = patch.object(UniversityBaseViewSet, 'initial',
            lambda self_view, request, *args, **kwargs: setattr(request, 'user', type('User', (), {'is_authenticated': True, 'is_anonymous': False})()) or super(UniversityBaseViewSet, self_view).initial(request, *args, **kwargs))
        self.auth_patch.start()

        # Create prerequisites - Now migrations should work via pytest-django
        try:
            response = self.client.post('/v1/university/teaching-units/',
                data={'code': 'ASMT101', 'name': 'Assessment Teaching Unit', 'teaching_prompt': 'TP'},
                content_type='application/json')
            assert response.status_code == 201, f"Teaching unit creation failed: {response.content.decode()}"
            self.tu_id = response.json()['id']

            response = self.client.post('/v1/university/courses/',
                data={ 'name': 'Assessment Course', 'code': 'ASMTC', 'coordinator': 'Coordinator', 'teaching_units': [self.tu_id], 'teaching_prompt': 'Course prompt' },
                content_type='application/json')
            assert response.status_code == 201, f"Course creation failed: {response.content.decode()}"
            self.course_id = response.json()['id']

            response = self.client.post('/v1/university/students/',
                data={'name': 'Assessment Student', 'gpa': '4.0', 'status': 'active'},
                content_type='application/json')
            assert response.status_code == 201, f"Student creation failed: {response.content.decode()}"
            self.student_id = response.json()['id']

            response = self.client.post('/v1/university/enrollments/',
                data={'student': self.student_id, 'teaching_unit': self.tu_id, 'status': 'enrolled'},
                content_type='application/json')
            assert response.status_code == 201, f"Enrollment creation failed: {response.content.decode()}"
            self.enrollment_id = response.json()['id']
        except Exception as e:
            pytest.fail(f"Failed to create prerequisites in setup_method: {e}")

        yield # Test runs here

        # Teardown patches
        self.auth_patch.stop()


    def test_create_and_get_assessment_item(self): # No client arg needed
        """Test creating and retrieving an assessment item."""
        # Test assumes setup_method was successful
        response = self.client.post('/v1/university/assessment-items/',
            data={ 'enrollment': self.enrollment_id, 'title': 'Integration Test Assessment', 'status': 'pending', 'due_date': '2025-03-01T09:00:00Z', 'weight': '20.00' },
            content_type='application/json')
        assert response.status_code == 201, f"Assessment item creation failed: {response.content.decode()}"
        ai_id = response.json()['id']

        response = self.client.get(f'/v1/university/assessment-items/{ai_id}/')
        assert response.status_code == 200
        assert 'Integration Test Assessment' in response.content.decode()

