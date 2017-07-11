import getopt
import signal
import sys
sys.path.append('.')
# Some IMU explanation https://github.com/richards-tech/RTIMULib/tree/master/Linux/python/tests
import RTIMU
import os.path
import time
import math
import os
import spidev_test as controller

from threading import Thread
###############################
# ORIENTATION GLOBALS
###############################
RUNNING = True
DESIRED_YAW = 0 # direction (radians)
DESIRED_PITCH = -0.175 # ground attack (radians)
SERVO_RANGE = 30
WING_PARAM = {
  "LEFT": {"CENTER": 60},
  "RIGHT": {"CENTER": 120}
}
INTEND_WING_LEFT = 0
INTEND_WING_RIGHT = 0

SETTINGS_FILE = "RTIMULib"
###############################

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


def getOrientation():
    data = imu.getIMUData()
    fusionPose = data["fusionPose"]
    roll = fusionPose[0]
    pitch = fusionPose[1]
    yaw = fusionPose[2]
    print("r: %f p: %f y: %f" % (
        math.degrees(roll), math.degrees(pitch), math.degrees(yaw))
    )
    return roll, pitch, yaw


def getDesiredRoll(yawDelta_rad):
    tanSigma = 2
    # tan cycles twice over 2pi, so scale rad_delta appropriately. 
    # We are getting a scalar between -1 and 1 here
    print "Delta: %f (%f)" % (yawDelta_rad, math.degrees(yawDelta_rad))
    tanScale = math.tan(yawDelta_rad/2)/tanSigma 
    if math.fabs(tanScale) > 1:
        tanScale = tanScale/math.fabs(tanScale) # limit it to 1
    maxAbsRange = math.pi/6 # Maximum absolute roll angle in radians(+/- 30degrees)
    return maxAbsRange * tanScale


def calculateWingAngle(roll, pitch, yaw, debug):
    # Initialize the wing adjustments at 0
    # We will add up all adjustments, then scale them to the ranges of the servos.
    wing_left = 0
    wing_right = 0
    # Now adjust for pitch
    deltaPitch = DESIRED_PITCH - pitch
    wing_left += deltaPitch
    wing_right += deltaPitch
    # Calculate a desired roll from our yaw
    deltaYaw = min(DESIRED_YAW - yaw, yaw - DESIRED_YAW)
    desired_roll = getDesiredRoll(deltaYaw)
    deltaRoll = desired_roll - roll # This is radians
    # Adjust the wings again for roll
    wing_left += deltaRoll
    wing_right -= deltaRoll
    # Scale these angles now based on maximum ranges of the servos
    maxAngle = max(math.fabs(wing_left), math.fabs(wing_right))
    wing_left_scaled = wing_left
    wing_right_scaled = wing_right
    if maxAngle > math.radians(SERVO_RANGE):
        angleScale = maxAngle/math.radians(SERVO_RANGE)
        wing_left_scaled /= angleScale
        wing_right_scaled /= angleScale
    # Calculate servo degrees
    # Return new wing angles
    wing_left_servo = WING_PARAM['LEFT']['CENTER'] + math.degrees(wing_left_scaled)
    wing_right_servo = WING_PARAM['RIGHT']['CENTER'] - math.degrees(wing_right_scaled)

    if debug:
        print("PITCH: %f\nROLL: %f" % (
            math.degrees(deltaPitch), math.degrees(deltaRoll))
        )
        print ("LEFT:\n\tRAW: %f\n\tSCALED: %f\n\tSERVO: %f" % (
            math.degrees(wing_left), 
            math.degrees(wing_left_scaled),
            wing_left_servo)
        )
        print ("RIGHT:\n\tRAW: %f\n\tSCALED: %f\n\tSERVO: %f" % (
            math.degrees(wing_right), 
            math.degrees(wing_right_scaled),
            wing_right_servo)
        )
    print "%2.2f %2.2f" % (wing_left_servo, wing_right_servo)
    return wing_left_servo, wing_right_servo


def update_target_wings():
    global INTEND_WING_LEFT
    global INTEND_WING_RIGHT
    
    counter = 0
    while RUNNING:
        goodIMU = imu.IMURead() # We MUST read it this fast. Otherwise its shite.
        time.sleep(poll_interval*1.0/1000.0)

        counter += 1
        if goodIMU:
            debug=(counter % 50 == 0)
            roll, pitch, yaw = getOrientation()
            INTEND_WING_LEFT, INTEND_WING_RIGHT = calculateWingAngle(roll, pitch, yaw, debug=debug)


def set_servo_angles():
    while RUNNING:
        wl = math.ceil(INTEND_WING_LEFT)
        wr = math.ceil(INTEND_WING_RIGHT)
        controller.W_glider_command("W:%s:%s" % (wl, wr))


def stop_test(signal, frame):
    global RUNNING
    print('You pressed Ctrl+C!')
    RUNNING = False
    sys.exit(0)


if __name__ == '__main__':
    signal.signal(signal.SIGINT, stop_test)
    controller.reset_spi()
    orientThread = Thread( target=update_target_wings, args=() )
    servoThread = Thread( target=set_servo_angles, args=() )

    orientThread.start()
    servoThread.start()
    while True:
        time.sleep(1) # Keep this thread active