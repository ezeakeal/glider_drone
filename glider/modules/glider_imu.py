import math
import redis
import logging
from . import glider_config


##############################################
# GLOBALS
##############################################
LOG = logging.getLogger("glider.%s" % __name__)

class IMU(object):

    """
    IMU class for obtaining orientation data

    All config and actual work is in 'imu_reader.py'
    It had to be run as a separate process for reasons unknown
    But if you try run IMU stuff in a class like this it will break!
    """
    imu = None

    offset_yaw= 0

    def __init__(self):
        self.redis_client = redis.StrictRedis(
            host=glider_config.get("redis_client", "host"),
            port=glider_config.get("redis_client", "port"),
            db=glider_config.get("redis_client", "db")
        )
        self.heading_discrepancy_tolerance_degrees = glider_config.getfloat("flight", "heading_discrepancy_allowance")

    def _val_or_default(self, name, default=0.0):
        val = self.redis_client.get(name)
        if not val:
            return default
        return float(val)

    def correct_heading(self, gps_heading):
        imu_heading = self.yaw
        gps_heading_rad = math.radians(gps_heading)
        if math.degrees(math.fabs(gps_heading_rad - imu_heading)) < self.heading_discrepancy_tolerance_degrees:
            LOG.info("Heading offset within tolerance of %s deg" % self.heading_discrepancy_tolerance_degrees)
        else:
            raw_yaw = imu_heading - self.offset_yaw
            self.offset_yaw = gps_heading_rad - raw_yaw
            LOG.info("Updated heading offset - currently %s degrees" % math.degrees(self.offset_yaw))

    @property
    def roll(self):
        return self._val_or_default("roll")

    @property
    def yaw(self):
        imu_val = self._val_or_default("yaw")
        imu_val += self.offset_yaw
        return imu_val

    @property
    def pitch(self):
        return self._val_or_default("pitch")
