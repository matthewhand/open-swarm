import os
os.environ.setdefault('ENABLE_API_AUTH', 'false')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'swarm.settings')
os.environ.setdefault('SQLITE_DB_PATH', f"/tmp/test_db_{os.urandom(8).hex()}.sqlite3")
import django
django.setup()
from django.test import TestCase, Client
from unittest.mock import patch
from blueprints.university.blueprint_university import UniversitySupportBlueprint

class AssessmentItemIntegrationTests(TestCase):
    def setUp(self):
        os.environ["SWARM_BLUEPRINTS"] = "university"  # Limit to university blueprint
        # Ensure API authentication is disabled
        self.env_patch = patch.dict(os.environ, {"ENABLE_API_AUTH": "false", "API_AUTH_TOKEN": ""}, clear=False)
        self.env_patch.start()
        # Patch UniversityBaseViewSet.initial to bypass authentication
        from blueprints.university.views import UniversityBaseViewSet
        self.auth_patch = patch.object(UniversityBaseViewSet, 'initial', 
            lambda self, request, *args, **kwargs: setattr(request, 'user', type('User', (), {'is_authenticated': True, 'is_anonymous': False})()) or super(UniversityBaseViewSet, self).initial(request, *args, **kwargs))
        self.auth_patch.start()
        # Register blueprint URLs
        dummy_config = {
            "llm": {"default": {"provider": "openai", "model": "gpt-4o", "base_url": "https://api.openai.com/v1", "api_key": "dummy"}}
        }
        blueprint = UniversitySupportBlueprint(config=dummy_config)
        blueprint.register_blueprint_urls()
        self.client = Client()
        # Create prerequisites
        response = self.client.post('/v1/university/teaching-units/',
            data={'code': 'ASMT101', 'name': 'Assessment Teaching Unit', 'teaching_prompt': 'TP'},
            content_type='application/json')
        self.assertEqual(response.status_code, 201, f"Teaching unit creation failed: {response.content}")

        response = self.client.post('/v1/university/courses/',
            data={
                'name': 'Assessment Course',
                'code': 'ASMTC',
                'coordinator': 'Coordinator',
                'teaching_units': [1],
                'teaching_prompt': 'Course prompt'
            },
            content_type='application/json')
        self.assertEqual(response.status_code, 201, f"Course creation failed: {response.content}")

        response = self.client.post('/v1/university/students/',
            data={'name': 'Assessment Student', 'gpa': '4.0', 'status': 'active'},
            content_type='application/json')
        self.assertEqual(response.status_code, 201, f"Student creation failed: {response.content}")

        response = self.client.post('/v1/university/enrollments/',
            data={'student': 1, 'teaching_unit': 1, 'status': 'enrolled'},
            content_type='application/json')
        self.assertEqual(response.status_code, 201, f"Enrollment creation failed: {response.content}")

    def tearDown(self):
        self.auth_patch.stop()
        self.env_patch.stop()
        os.environ.pop("SWARM_BLUEPRINTS", None)
        if os.path.exists(os.environ["SQLITE_DB_PATH"]):
            os.remove(os.environ["SQLITE_DB_PATH"])

    def test_create_and_get_assessment_item(self):
        response = self.client.post('/v1/university/assessment-items/',
            data={
                'enrollment': 1,
                'title': 'Integration Test Assessment',
                'status': 'pending',
                'due_date': '2025-03-01T09:00:00Z',
                'weight': '20.00'
            },
            content_type='application/json')
        self.assertEqual(response.status_code, 201, f"Assessment item creation failed: {response.content}")

        response = self.client.get('/v1/university/assessment-items/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('Integration Test Assessment', response.content.decode())
