import sys
import time
import math
import redis
import logging
import traceback
from threading import Thread

import RTIMU

from glider.settings import *

sys.path.append('.')

##############################################
# GLOBALS
##############################################
LOG = setup_custom_logger('imu')

class IMU(object):

    """
    IMU class for obtaining orientation data
    """
    imu = None
    settings_path="/RTIMULib"

    def __init__(self, poll_interval_ms=10.):
        self.threadAlive = False
        self.roll = 0
        self.pitch = 0
        self.yaw = 0
        self.poll_interval_ms = poll_interval_ms

    def init_imu(self):
        LOG.info("Using/Creating settings: %s.ini (exists: %s)" % 
            (self.settings_path, os.path.exists(self.settings_path)))
        self.imu = RTIMU.RTIMU(
            RTIMU.Settings(self.settings_path)
        )

        LOG.info("IMU Name: " + self.imu.IMUName())
        if (not self.imu.IMUInit()):
            LOG.critical("IMU Init Failed")
            sys.exit(1)
        else:
            LOG.info("IMU Init Succeeded")

    def configure_imu(self):
        self.imu.setSlerpPower(0.02)
        self.imu.setGyroEnable(True)
        self.imu.setAccelEnable(True)
        self.imu.setCompassEnable(False)

        self.poll_interval_ms = self.imu.IMUGetPollInterval()

    def start(self):
        self.init_imu()
        readerThread = Thread(target=self.readRedisOrientation, args=())
        LOG.info("Starting up orientation reader")
        self.threadAlive = True
        readerThread.start()

    def stop(self):
        self.threadAlive = False

    def readRedisOrientation(self):
        while self.threadAlive:
            if imu.IMURead():
                r,p,y = imu.getFusionData()
                self.roll = r
                self.pitch = p
                self.yaw = y
                time.sleep(poll_interval*1.0/1000.0)
