import redis
import logging
from config import glider_config

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
    # settings_path = glider_config.get("imu", "rtimu_conf")
    settings_path = "RTIMULib"

    def __init__(self):
        self.redis_client = redis.StrictRedis(
            host=glider_config.get("redis_client", "host"),
            port=glider_config.get("redis_client", "port"),
            db=glider_config.get("redis_client", "db")
        )

    @property
    def roll(self):
        return self.redis_client.get("roll")

    @property
    def yaw(self):
        return self.redis_client.get("yaw")

    @property
    def pitch(self):
        return self.redis_client.get("pitch")
