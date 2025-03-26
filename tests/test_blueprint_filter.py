import unittest
from swarm.extensions.blueprint.blueprint_utils import filter_blueprints

class BlueprintFilterTestCase(unittest.TestCase):
    def test_filter_blueprints(self):
        # Given a sample blueprints dictionary
        blueprints = {
            "echo": {"title": "Echo Blueprint"},
            "suggestion": {"title": "Suggestion Blueprint"},
            "university": {"title": "University Blueprint"},
            "other": {"title": "Other Blueprint"}
        }
        # When filtering with allowed blueprints "echo,suggestion,university"
        filtered = filter_blueprints(blueprints, "echo,suggestion,university")
        # Then only the allowed keys should remain
        expected = {
            "echo": {"title": "Echo Blueprint"},
            "suggestion": {"title": "Suggestion Blueprint"},
            "university": {"title": "University Blueprint"}
        }
        self.assertEqual(filtered, expected)

if __name__ == "__main__":
    unittest.main()