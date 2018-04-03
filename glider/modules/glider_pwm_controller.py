import math
import time
import logging
# noinspection PyUnresolvedReferences
import Adafruit_PCA9685
from threading import Thread
from . import glider_config

LOG = logging.getLogger("glider.%s" % __name__)


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

    # We COULD lump this in with flap_addresses and angles, but I don't want code to ever accidentally trigger a release
    servo_addresses = {"parachute": None, "release": None}
    servo_angles = {"parachute": None, "release": None}

    flap_addresses = {'rudder': None, 'rear': None,
                       'left_near': None, 'right_near': None,
                       'left_far': None, 'right_far': None}

    flap_angles = {'rudder': None, 'rear': None,
                    'left_near': None, 'right_near': None,
                    'left_far': None, 'right_far': None}

    flap_ranges = {'rudder': None, 'rear': None,
                    'left_near': None, 'right_near': None,
                    'left_far': None, 'right_far': None}

    _current_flap_angles = {} # Used to maintain the current angle and reduce calls to the PWM controller (unused)

    def __init__(self):
        LOG.debug("Staring up PWM Controller (Address=%s Frequency=%shz)" % (self.address, self.frequency))
        self.pwm = Adafruit_PCA9685.PCA9685(address=int(self.address, 16))
        self.pwm.set_pwm_freq(self.frequency)
        self._read_flap_config()
        self.start()

    def _read_flap_config(self):
        for flap in self.flap_addresses.keys():
            self.flap_addresses[flap] = glider_config.getint("servo", "flap_address_%s" % flap)
            flap_angle_range = [float(x) for x in glider_config.get("flight", "flap_range_%s" % flap).split(",")]
            self.flap_ranges[flap] = flap_angle_range
            self.flap_angles[flap] = sum(flap_angle_range)/2
        for servo in self.servo_addresses.keys():
            self.servo_addresses[servo] = glider_config.getint("servo", "servo_address_%s" % servo)
            self.servo_angles[servo] = glider_config.getfloat("servo", "servo_center_%s" % servo)

    def start(self):
        servo_update_thread = Thread( target=self.update_servo_angles, args=() )
        self.threadAlive = True
        LOG.info("Setting initial servo position")
        self.servo_init_position()
        LOG.info("Starting up Servo Controller thread now")
        servo_update_thread.start()

    def servo_init_position(self, delay=0.5):
        for flap, address in self.flap_addresses.items():
            center_angle = self.flap_angles[flap]
            self._set_servo_angle(address, center_angle , self.servo_min_ms, self.servo_max_ms, force=True)
            time.sleep(delay)

    def stop(self):
        self.servo_init_position(delay=0.1)
        time.sleep(1)
        self.threadAlive = False

    def update_servo_angles(self):
        while self.threadAlive:
            for flap_id, angle in self.flap_angles.items():
                servo_address = self.flap_addresses[flap_id]
                self._set_servo_angle(servo_address, angle, flap_id=flap_id)
            for servo_id, angle in self.servo_angles.items():
                servo_address = self.servo_addresses[servo_id]
                self._set_servo_angle(servo_address, angle, flap_id=flap_id)
            time.sleep(self.controller_breather) # Sleep at least this much - can happen if there are no angle updates

    def _set_servo_angle(self, servo_address, angle, min_ms=None, max_ms=None, force=False, flap_id=None):
        if not min_ms:
            min_ms = self.servo_min_ms
        if not max_ms:
            max_ms = self.servo_max_ms

        angle = math.ceil(angle)  # round the angle to reduce calls for minor adjustments
        if not force and flap_id:
            if angle == self.flap_angles[flap_id]:
                return

        ms_range = float(max_ms - min_ms)
        LOG.debug("Servo pulse ms range: %s" % ms_range)
        # This is the pulse we add to the initial pulse of 1ms to change the angle
        # e.g. 1ms = 0deg, 2ms = 180deg, so angle_pulse of 0.5 results in 1.5 = 90deg
        angle_pulse = (angle/180.0 * ms_range)
        LOG.debug("Angle fraction (%s = %s)" % (angle, angle_pulse))
        pulse_width = int(4096/(1000/self.frequency)*(min_ms + angle_pulse))
        LOG.info("Setting servo(%s) pulse (fraction=%s duration=%sms)" % (
            servo_address, min_ms+angle_pulse, pulse_width))
        self.pwm.set_pwm(servo_address, self.servo_pulse_lag, pulse_width + self.servo_pulse_lag)
        time.sleep(self.controller_breather)

    # def set_flap_angles(self, angle_dictionary):
    #     LOG.debug("Setting flaps: %s" % (angle_dictionary))
    #     self.flap_angles.update(angle_dictionary)

    def set_flap_scales(self, scale_angle_dictionary):
        # Used to take in a range between 0 and 1 and set the angle accordingly between the servo min/max
        # 0.5 would be center flap for neutral
        LOG.debug("Setting flap scales: %s" % (scale_angle_dictionary))
        for flap, scale in scale_angle_dictionary.items():
            angle_range = self.flap_ranges[flap]
            scaled_angle = angle_range[0] + scale*(angle_range[1]-angle_range[0])
            self.flap_angles[flap] = scaled_angle

    def release_parachute(self, reset=False):
        LOG.debug("Releasing parachute")
        angle_parachute = 180 if reset else 0
        self.servo_angles['parachute'] = angle_parachute

    def release_from_balloon(self, reset=False):
        LOG.debug("Releasing from balloon")
        angle_balloon_release = 10 if reset else 180
        self.servo_angles['release'] = angle_balloon_release
