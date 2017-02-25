import sys, getopt

sys.path.append('.')
import RTIMU
import os.path
import time
import math
import redis


SETTINGS_FILE = "/RTIMULib"
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

redis_client = redis.StrictRedis(
    host="127.0.0.1",
    port=6379,
    db=0
)

# this is a good time to set any fusion parameters
imu.setSlerpPower(0.02)
imu.setGyroEnable(True)
imu.setAccelEnable(True)
imu.setCompassEnable(False)

poll_interval = imu.IMUGetPollInterval()

print("Recommended Poll Interval: %dmS\n" % poll_interval)
while True:
  if imu.IMURead():
    r,p,y = imu.getFusionData()
    redis_client.set("p", p)
    redis_client.set("r", r)
    redis_client.set("y", y)

    time.sleep(poll_interval*1.0/1000.0)