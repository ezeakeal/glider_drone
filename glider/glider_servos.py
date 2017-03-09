import os
import logging

from gps import *
from time import *
from glider.settings import *
# GUIDE
# http://ava.upuaut.net/?p=768

LOG = setup_custom_logger('glider_servo_controller')


class GliderServoController(object):

    def __init__(self):
        LOG.debug("Staring up ServoController")

    def set_wings(self, angle_left_radians, angle_right_radians):
        LOG.debug("Setting Wings: Left(%s) Right(%s)" % (angle_left_radians, angle_right_radians))

    def release_parachute(self):
        LOG.debug("Releasing parachute")

    def release_from_balloon(self):
        LOG.debug("Releasing from balloon")
