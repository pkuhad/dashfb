from django.test import TestCase
from fb_client.apps.fbschema.utils import *
from fb_client.apps.fbschema.models import *

class UtilityMethodTestcases(TestCase):
    def get_fields_from_model_test(self):
        self.assertIsInstance(get_fields_from_model, 'str')
'''
class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.assertEqual(1 + 1, 2)
'''        
