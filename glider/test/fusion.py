import sys, getopt

sys.path.append('.')
import RTIMU
import os.path
import time
import math


SETTINGS_FILE = "RTIMULib"
print("Using settings file " + SETTINGS_FILE + ".ini")
if not os.path.exists(SETTINGS_FILE + ".ini"):
  print("Settings file does not exist, will be created")

s = RTIMU.Settings(SETTINGS_FILE)
imu = RTIMU.RTIMU(s)

print("IMU Name: " + imu.IMUName())

if (not imu.IMUInit()):
    print("IMU Init Failed")
    sys.exit(1)
else:
    print("IMU Init Succeeded")

# this is a good time to set any fusion parameters

imu.setSlerpPower(0.02)
imu.setGyroEnable(True)
imu.setAccelEnable(True)
imu.setCompassEnable(True)

poll_interval = imu.IMUGetPollInterval()

print("Recommended Poll Interval: %dmS\n" % poll_interval)
while True:
  if imu.IMURead():
    r,p,y = imu.getFusionData()
    print("r: %f p: %f y: %f" % (math.degrees(r), 
        math.degrees(p), math.degrees(y)))
    time.sleep(poll_interval*1.0/1000.0)
