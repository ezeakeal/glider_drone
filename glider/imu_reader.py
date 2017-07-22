import sys

sys.path.append('.')
import RTIMU
import os.path
import time
import redis

from config import glider_config
SETTINGS_FILE = glider_config.get("imu", "conf_path")

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
    host=glider_config.get("redis_client", "host"),
    port=glider_config.get("redis_client", "port"),
    db=glider_config.get("redis_client", "db")
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
    redis_client.set("roll", r)
    redis_client.set("pitch", p)
    redis_client.set("yaw", y)

    time.sleep(poll_interval*1.0/1000.0)