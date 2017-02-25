import time
import math
import RTIMU
from threading import Thread


# if IMU still weird: https://github.com/micropython-IMU/micropython-mpu9x50

##############################################
# GLOBALS
##############################################
SETTINGS_FILE = "RTIMULib"
s = RTIMU.Settings(SETTINGS_FILE)
imu = RTIMU.RTIMU(s)
imu.IMUInit()

imu.setSlerpPower(0.02)
imu.setGyroEnable(True)
imu.setAccelEnable(True)
imu.setCompassEnable(True)

class IMU(object):
    """
    IMU class for obtaining orientation data
    """
    def __init__(self):
        self.O_IMU = imu
        self.threadAlive = False
        self.configureOrientationChip()
        
        self.roll = 0
        self.pitch = 0
        self.yaw = 0
        
        self.poll_interval = self.getOrientPollInterval()

    def getOrientPollInterval(self):
        poll_interval = self.O_IMU.IMUGetPollInterval()
        print ("Recommended Poll Interval: %dmS\n" % poll_interval)
        return poll_interval

    def configureOrientationChip(self):
        self.O_IMU.setSlerpPower(0.02)
        self.O_IMU.setGyroEnable(True)
        self.O_IMU.setAccelEnable(True)
        self.O_IMU.setCompassEnable(True)

    def start(self):
        sensorThread = Thread( target=self.updateOrientation, args=() )
        self.threadAlive = True
        print ("Starting up orienation thread now")
        sensorThread.start()

    def stop(self):
        self.threadAlive = False

    def updateOrientation(self):
        while self.threadAlive:
            if self.O_IMU.IMURead():
                p,r,y = self.O_IMU.getFusionData()
                ######## NOTE: THIS MUST BE INSPECTED! CHECK THIS IS RIGHT!
                self.pitch = float(p)
                self.roll = float(r)
                self.yaw = float(y)
            time.sleep(self.poll_interval*1.0/1000.0)

if __name__ == '__main__':
    i = IMU()
    i.start()
    while True:
        try:
            time.sleep(.05)
            print "R:%03.02f P:%03.02f Y:%03.02f" % (
                math.degrees(i.roll), math.degrees(i.pitch), math.degrees(i.yaw)
            )
        except KeyboardInterrupt:
            i.stop()
            break

        