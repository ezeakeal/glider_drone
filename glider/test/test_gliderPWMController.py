import time
from glider.glider_pwm_controller import GliderPWMController
from unittest import TestCase


class TestGliderPWMController(TestCase):
    def setUp(self):
        self.PWM = GliderPWMController()
        time.sleep(2)

    def tearDown(self):
        self.PWM.stop()

    def test_set_wings(self):
        for ang_diff in [0, 45, 90, 135, 180]:
            self.PWM.set_wings(ang_diff, ang_diff)
            time.sleep(0.5)

    def test_release_parachute(self):
        self.PWM.release_parachute()

    def test_release_from_balloon(self):
        self.PWM.release_from_balloon()
