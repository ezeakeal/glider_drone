import log
import time
import math
import redis
import logging
import traceback
from threading import Thread

##############################################
# GLOBALS
##############################################
LOG = log.setup_custom_logger('imu')
LOG.setLevel(logging.WARN)

class IMU(object):

    """
    IMU class for obtaining orientation data
    """

    def __init__(self, GPS, poll_interval_ms=10.,
        roll_offset=0, yaw_offset=0, pitch_offset=0):
        self.threadAlive = False
        self.roll = 0
        self.pitch = 0
        self.yaw = 0
        self.GPS = GPS
        self.roll_offset = roll_offset
        self.yaw_offset = yaw_offset
        self.pitch_offset = pitch_offset
        self.poll_interval_ms = poll_interval_ms
        self.setup_redis_conn()

    def setup_redis_conn(self):
        self.redis_client = redis.StrictRedis(
            host="127.0.0.1",
            port=6379,
            db=0
        )

    def start(self):
        readerThread = Thread(target=self.readRedisOrientation, args=())
        LOG.info("Starting up orienation reader thread now")
        self.threadAlive = True
        readerThread.start()

    def stop(self):
        self.threadAlive = False

    def readRedisOrientation(self):
        while self.threadAlive:
            self.pitch = float(self.redis_client.get("p")) + float(self.pitch_offset) # Switched because I mounted the chip wrong..
            self.roll = float(self.redis_client.get("r")) + float(self.roll_offset) 
            self.yaw = float(self.redis_client.get("y")) + float(self.yaw_offset)
            if abs(self.yaw) > 180:
                self.yaw = ((self.yaw + 180) % 360) - 180
            LOG.debug("p: %f r: %f y: %f" % (
                math.degrees(self.pitch), math.degrees(self.roll), math.degrees(self.yaw))
            )
            gps_track = self.GPS.gpsd.fix.track
            if gps_track and not math.isnan(gps_track):
                LOG.warning("Updating GPS track. Yaw offset = %s" % gps_track)
                self.yaw_offset = gps_track - self.yaw
            time.sleep(self.poll_interval_ms/1000.0)
