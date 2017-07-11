from unittest import TestCase
from glider.glider_camera import GliderCamera

class TestGliderCamera(TestCase):
    def setUp(self):
        self.camera = GliderCamera()

    def tearDown(self):
        self.camera.stop()

    def test_get_cam(self):
        cam = self.camera.get_cam("low")
        assert(cam.resolution == (640, 480))

    def test_take_video(self):
        cam = self.camera.take_video(1)

    def test_take_low_pic(self):
        self.fail()

    def test_take_high_pic(self):
        self.fail()

    def test_take_pictures(self):
        self.fail()
