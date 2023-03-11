import json
import unittest

from app import app

class TestApp(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()

    def test_hello_world(self):
        response = self.app.get('/')
        data = json.loads(response.data)
        self.assertEqual(data['message'], 'Hello, World!')

if __name__ == '__main__':
    unittest.main()
