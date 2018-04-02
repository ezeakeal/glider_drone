import time
from glider.modules.glider_pilot import Pilot
from glider.modules.glider_pwm_controller import GliderPWMController
from unittest import TestCase

class FakeIMU(object):
    def __init__(self):
        self._r = None
        self._p = None
        self._y = None

    @property
    def roll(self):
        return self._r
    @property
    def yaw(self):
        return self._y
    @property
    def pitch(self):
        return self._p

    @roll.setter
    def roll(self, value):
        self._r = value
    @pitch.setter
    def pitch(self, value):
        self._p = value
    @yaw.setter
    def yaw(self, value):
        self._y = value


class TestGliderPWMController(TestCase):
    def setUp(self):
        self.imu_reader = FakeIMU()
        self.pilot = Pilot(self.imu_reader)
        self.PWM = GliderPWMController()
        time.sleep(0.5)

    def tearDown(self):
        self.PWM.stop()
        self.pilot.stop()

    def test_heading_rotation(self):
        for angle in range(-360, 720, 10):
            self.imu_reader.yaw = angle
            time.sleep(0.01)
