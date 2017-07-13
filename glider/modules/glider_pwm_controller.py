import math
import time
import logging
# noinspection PyUnresolvedReferences
import Adafruit_PCA9685
from threading import Thread
from . import glider_config

LOG = logging.getLogger('glider_servo_controller')


class GliderPWMController(object):
    """
    Threaded PWM controller.
    Although the microcontroller is managing the servo angles in its own time,
    if we write too many angles to the servos at once, they all go nuts!
    So instead we will set desired angle, and a thread will iterate over
    and update all servo angles in sequence with some delay.
    """

    threadAlive = False

    address = glider_config.get("servo", "hat_i2c_address")
    frequency = glider_config.getint("servo", "frequency")
    servo_pulse_lag = glider_config.getint("servo", "pulse_lag_ms")
    controller_breather = glider_config.getfloat("servo", "controller_breather")

    servo_min_ms = glider_config.getfloat("servo", "min_ms")
    servo_max_ms = glider_config.getfloat("servo", "max_ms")

    addr_wingl = glider_config.getint("servo", "address_wing_left")
    addr_wingr = glider_config.getint("servo", "address_wing_right")
    addr_chute = glider_config.getint("servo", "address_parachute")
    addr_relse = glider_config.getint("servo", "address_release")

    # Initialize all angles, and set the old values to a different value to trigger servo update
    # [desired_value, current_value]
    # If they match, no servo signal is sent to the servo hat
    angle_wing_l = [90, -1]
    angle_wing_r = [90, -1]
    angle_parachute = [0, -1]
    angle_balloon_release = [0, -1]

    def __init__(self):
        LOG.debug("Staring up PWM Controller (Address=%s Frequency=%shz)" % (self.address, self.frequency))
        self.pwm = Adafruit_PCA9685.PCA9685(address=int(self.address, 16))
        self.pwm.set_pwm_freq(self.frequency)
        self.start()

    def start(self):
        servo_update_thread = Thread( target=self.update_servo_angles, args=() )
        self.threadAlive = True
        LOG.info("Starting up Servo Controller thread now")
        servo_update_thread.start()

    def stop(self):
        self.threadAlive = False

    def update_servo_angles(self):
        while self.threadAlive:
            self._set_servo_angle(
                self.addr_wingl, self.angle_wing_l,
                self.servo_min_ms, self.servo_max_ms
            )
            self._set_servo_angle(
                self.addr_wingr, self.angle_wing_r,
                self.servo_max_ms, self.servo_min_ms  # Invert because servo is flipped on other side
            )
            self._set_servo_angle(
                self.addr_relse, self.angle_balloon_release,
                self.servo_min_ms, self.servo_max_ms
            )
            self._set_servo_angle(
                self.addr_chute, self.angle_parachute,
                self.servo_min_ms, self.servo_max_ms
            )
            time.sleep(0.01)

    def _set_servo_angle(self, servo_address, angle_pair, min_ms, max_ms):
        if angle_pair[0] == angle_pair[1]: # The new angle and old angle are the same
            return
        else: # The new angle is different!
            angle_pair[1] = angle_pair[0]
        angle = math.ceil(angle_pair[0])  # round the angle to reduce calls for minor adjustments
        ms_range = float(max_ms - min_ms)
        LOG.debug("Servo pulse ms range: %s" % ms_range)
        # This is the pulse we add to the initial pulse of 1ms to change the angle
        # e.g. 1ms = 0deg, 2ms = 180deg, so angle_pulse of 0.5 results in 1.5 = 90deg
        angle_pulse = (angle/ 180.0 * ms_range)
        LOG.debug("Angle fraction (%s = %s)" % (angle, angle_pulse))
        pulse_width = int(4096/(1000/self.frequency)*(min_ms + angle_pulse))
        LOG.info("Setting servo(%s) pulse (fraction=%s duration=%sms)" % (
            servo_address, min_ms+angle_pulse, pulse_width)
                 )
        self.pwm.set_pwm(servo_address, self.servo_pulse_lag, int(pulse_width + self.servo_pulse_lag))
        time.sleep(self.controller_breather)

    def set_wings(self, angle_left_degrees, angle_right_degrees):
        LOG.debug("Setting Wings: Left(%s) Right(%s)" % (angle_left_degrees, angle_right_degrees))
        self.angle_wing_l[0] = angle_left_degrees
        self.angle_wing_r[0] = angle_right_degrees

    def release_parachute(self):
        LOG.debug("Releasing parachute")
        self.angle_parachute[0] = 180

    def release_from_balloon(self):
        LOG.debug("Releasing from balloon")
        self.angle_balloon_release[0] = 180
