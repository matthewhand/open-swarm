import os
# Set env vars before Django imports
os.environ.setdefault('ENABLE_API_AUTH', 'false')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'swarm.settings')
os.environ["SWARM_BLUEPRINTS"] = "university" # Required by conftest/settings

import django
import sys
import types # For dynamic module creation
from django.conf import settings
if not settings.configured:
     django.setup() # Setup should happen via conftest, but ensure it runs

# --- Imports after setup ---
from django.test import TestCase, Client, override_settings # Need override_settings for ROOT_URLCONF
from django.urls import path, include, clear_url_caches, set_urlconf
from unittest.mock import patch
# from django.core.management import call_command # No manual migrate needed

# No INSTALLED_APPS override needed, settings.py handles it
# Only override ROOT_URLCONF to point to our dynamic one
@override_settings(
    ROOT_URLCONF=__name__ + '.temp_urls_assessment'
    # INSTALLED_APPS=... # REMOVED
)
class AssessmentItemIntegrationTests(TestCase):
    temp_urls_assessment = None

    @classmethod
    def setUpClass(cls):
        # Don't call super().setUpClass() yet, we need to create the module first
        try:
            # Create dynamic URLconf
            from blueprints.university import urls as university_urls
            from swarm import urls as swarm_urls
            core_patterns = [p for p in swarm_urls.urlpatterns if not str(getattr(p, 'pattern','')).startswith('v1/university/')]
            test_urlpatterns = core_patterns + [path('v1/university/', include((university_urls, 'university')))]
            cls.temp_urls_assessment = types.ModuleType(__name__ + '.temp_urls_assessment')
            cls.temp_urls_assessment.urlpatterns = test_urlpatterns
            sys.modules[__name__ + '.temp_urls_assessment'] = cls.temp_urls_assessment
            print(f"Created temporary URLconf module: {__name__ + '.temp_urls_assessment'}")
            clear_url_caches()
            # Now call super().setUpClass() which applies the override_settings context
            super().setUpClass()
            # Migrations should have been handled by pytest-django based on settings.py

        except Exception as e:
             print(f"ERROR in setUpClass: {e}")
             # Ensure teardown is attempted
             try: super(AssessmentItemIntegrationTests, cls).tearDownClass()
             except Exception as td_e: print(f"Error during tearDownClass: {td_e}")
             raise

    @classmethod
    def tearDownClass(cls):
        # Clean up dynamic module
        if cls.temp_urls_assessment and (__name__ + '.temp_urls_assessment') in sys.modules:
             del sys.modules[__name__ + '.temp_urls_assessment']
        # URLConf reversion handled by override_settings context manager exit
        clear_url_caches()
        print(f"Cleaned up temporary URLconf.")
        super().tearDownClass()


    def setUp(self):
        self.env_patch = patch.dict(os.environ, {"ENABLE_API_AUTH": "false", "API_AUTH_TOKEN": ""}, clear=False)
        self.env_patch.start()
        from blueprints.university.views import UniversityBaseViewSet
        self.auth_patch = patch.object(UniversityBaseViewSet, 'initial',
            lambda self, request, *args, **kwargs: setattr(request, 'user', type('User', (), {'is_authenticated': True, 'is_anonymous': False})()) or super(UniversityBaseViewSet, self).initial(request, *args, **kwargs))
        self.auth_patch.start()
        self.client = Client() # Client created within override_settings context

        # Prerequisite creation - DB should be migrated, URLs should resolve
        response = self.client.post('/v1/university/teaching-units/',
            data={'code': 'ASMT101', 'name': 'Assessment Teaching Unit', 'teaching_prompt': 'TP'},
            content_type='application/json')
        self.assertEqual(response.status_code, 201, f"Teaching unit creation failed: {response.content.decode()}")
        self.tu_id = response.json()['id']

        response = self.client.post('/v1/university/courses/',
            data={ 'name': 'Assessment Course', 'code': 'ASMTC', 'coordinator': 'Coordinator', 'teaching_units': [self.tu_id], 'teaching_prompt': 'Course prompt' },
            content_type='application/json')
        self.assertEqual(response.status_code, 201, f"Course creation failed: {response.content.decode()}")
        self.course_id = response.json()['id']

        response = self.client.post('/v1/university/students/',
            data={'name': 'Assessment Student', 'gpa': '4.0', 'status': 'active'},
            content_type='application/json')
        self.assertEqual(response.status_code, 201, f"Student creation failed: {response.content.decode()}")
        self.student_id = response.json()['id']

        response = self.client.post('/v1/university/enrollments/',
            data={'student': self.student_id, 'teaching_unit': self.tu_id, 'status': 'enrolled'},
            content_type='application/json')
        self.assertEqual(response.status_code, 201, f"Enrollment creation failed: {response.content.decode()}")
        self.enrollment_id = response.json()['id']

    def tearDown(self):
        self.auth_patch.stop()
        self.env_patch.stop()

    def test_create_and_get_assessment_item(self):
        response = self.client.post('/v1/university/assessment-items/',
            data={ 'enrollment': self.enrollment_id, 'title': 'Integration Test Assessment', 'status': 'pending', 'due_date': '2025-03-01T09:00:00Z', 'weight': '20.00' },
            content_type='application/json')
        self.assertEqual(response.status_code, 201, f"Assessment item creation failed: {response.content.decode()}")
        ai_id = response.json()['id']

        response = self.client.get(f'/v1/university/assessment-items/{ai_id}/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('Integration Test Assessment', response.content.decode())
