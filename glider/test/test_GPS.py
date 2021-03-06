from unittest import TestCase
from glider.modules.glider_gps import GPS

class TestGPS(TestCase):

    def setUp(self):
        self.gps = GPS()
        self.gps.start()

    def test_data(self):
        data = self.gps.data
        self.assertTrue(hasattr(data, "lon"))
        self.assertTrue(hasattr(data, "lat"))
        self.assertIsNotNone(data.lat)
        self.assertIsNotNone(data.lon)

    def tearDown(self):
        self.gps.stop()
