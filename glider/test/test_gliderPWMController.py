import time
from glider.modules.glider_pwm_controller import GliderPWMController
from unittest import TestCase


class TestGliderPWMController(TestCase):
    def setUp(self):
        self.PWM = GliderPWMController()
        time.sleep(0.5)

    def tearDown(self):
        self.PWM.stop()

    def test_set_wings(self):
        for ang_diff in range(90,180) + list(reversed(range(180))) + range(90):
            self.PWM.set_flaps(ang_diff, ang_diff)
            time.sleep(0.001)

    def test_release_parachute(self):
        self.PWM.release_parachute()
        time.sleep(1)

    def test_release_from_balloon(self):
        self.PWM.release_from_balloon()
        time.sleep(1)
