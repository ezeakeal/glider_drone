from unittest import TestCase

from glider.modules.glider_radio import GliderRadio

class TestGliderRadio(TestCase):
    def setUp(self):
        self.radio = GliderRadio(self.test_callback)
        self.radio.start()

    def tearDown(self):
        self.radio.stop()

    def test_callback(self, msgdict):
        print("Received message: %s" % msgdict)

    def test_send_data(self):
        self.radio.send_data(["test"])
