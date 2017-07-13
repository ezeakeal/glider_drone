import redis
import logging
from modules import glider_config

##############################################
# GLOBALS
##############################################
LOG = logging.getLogger("IMU")

class IMU(object):

    """
    IMU class for obtaining orientation data

    All config and actual work is in 'imu_reader.py'
    It had to be run as a separate process for reasons unknown
    But if you try run IMU stuff in a class like this it will break!
    """
    imu = None

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

    @property
    def roll(self):
        return self._val_or_default("roll")

    @property
    def yaw(self):
        return self._val_or_default("yaw")

    @property
    def pitch(self):
        return self._val_or_default("pitch")
