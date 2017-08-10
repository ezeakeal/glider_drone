import math
import redis
import logging
from modules import glider_config

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

    def _val_or_default(self, name, default=0.0):
        val = self.redis_client.get(name)
        if not val:
            return default
        return float(val)

    def correct_heading(self, gps_heading):
        imu_heading = self.yaw
        gps_heading_rad = math.radians(gps_heading)
        old_correction = self.offset_yaw
        self.offset_yaw = gps_heading_rad - (imu_heading - old_correction)
        correction = math.degrees(old_correction - self.offset_yaw)
        LOG.info("Corrected heading by %s degrees" % correction)
        return correction

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
