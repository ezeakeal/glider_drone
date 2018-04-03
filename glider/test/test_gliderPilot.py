import time
from glider.modules.glider_pilot import Pilot
from glider.modules.glider_pwm_controller import GliderPWMController
from unittest import TestCase
import math
rad = math.radians

class FakeIMU(object):
    def __init__(self):
        self._r = 0.0
        self._p = 0.0
        self._y = 0.0

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


class TestGliderPilot(TestCase):
    def setUp(self):
        self.imu_reader = FakeIMU()
        self.pilot = Pilot(self.imu_reader)
        self.pilot.desired_yaw = 0.0 # We want to head north always
        self.pwm_controller = GliderPWMController()
        self.pilot._center_all_flaps()
        time.sleep(0.5)

    def tearDown(self):
        self.pwm_controller.stop()

    def test_turn_right(self):
        for angle in range(0, -180, -3) + range(-180, 0, 3):
            self.imu_reader.yaw = rad(angle)
            flap_scales = self.pilot.update_flap_angles()
            print("Yaw: %s --> %s" % (angle, flap_scales['rudder']))
            self.pwm_controller.set_flap_scales(flap_scales)
            time.sleep(0.05)

    def test_turn_left(self):
        for angle in range(0, 180, 3) + range(180, 0, -3):
            self.imu_reader.yaw = rad(angle)
            flap_scales = self.pilot.update_flap_angles()
            print("Yaw: %s --> %s" % (angle, flap_scales['rudder']))
            self.pwm_controller.set_flap_scales(flap_scales)
            time.sleep(0.05)

    def test_pitching(self):
        self.pilot.desired_pitch_deg = 0
        for angle in range(-45, 45, 1) + range(45, 0, -1):
            self.imu_reader.pitch = rad(angle)
            flap_scales = self.pilot.update_flap_angles()
            self.pwm_controller.set_flap_scales({'rear': flap_scales['rear']})
            time.sleep(0.05)

    def test_speed_pitching(self):
        self.pilot.desired_pitch_deg = 0
        for speed in  range(45, 0, -1) + range(0, 45):
            self.pilot.scale_pitch_for_speed(speed)
            flap_scales = self.pilot.update_flap_angles()
            self.pwm_controller.set_flap_scales({'rear': flap_scales['rear']})
            time.sleep(0.05)
