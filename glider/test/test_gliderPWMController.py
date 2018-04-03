import time
from glider.modules.glider_pwm_controller import GliderPWMController
from unittest import TestCase


class TestGliderPWMController(TestCase):
    def setUp(self):
        self.PWM = GliderPWMController()
        self.PWM.servo_init_position(delay=0.5)
        time.sleep(0.5)

    def tearDown(self):
        self.PWM.servo_init_position(delay=0.5)
        self.PWM.stop()

    def test_servo_flap_center(self):
        print ("Servos centered")

    def test_set_servos(self):
        for servo_id, address in self.PWM.servo_addresses.items():
            print("Testing servo: %s at %s" % (servo_id, address))
            for ang_diff in range(90,45,-3) + range(45,135,3) + range(135,90,-3):
                self.PWM._set_servo_angle(address, ang_diff)
                time.sleep(0.001)

    def test_set_flaps(self):
        for flap_id, address in self.PWM.flap_addresses.items():
            print("Testing flap: %s at %s" % (flap_id, address))
            for ang_diff in range(90,45,-3) + range(45,135,3) + range(135,90,-3):
                self.PWM._set_servo_angle(address, ang_diff)
                time.sleep(0.001)

    def test_release_parachute(self):
        self.PWM.release_parachute()
        time.sleep(1)

    def test_release_from_balloon(self):
        self.PWM.release_from_balloon()
        time.sleep(1)
