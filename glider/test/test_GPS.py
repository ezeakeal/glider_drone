from unittest import TestCase
from glider.glider_gps import GPS_USB

class TestGPS(TestCase):
    def test_data(self):
        gps = GPS_USB()
        gps.start()
        data = gps.data
        assert(hasattr(data, "lon"))
        assert(hasattr(data, "lat"))
        assert(getattr(data, "lat") is not None)
        gps.stop()
