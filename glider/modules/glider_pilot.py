import time
import math
import logging
from threading import Thread
from . import glider_config

##############################################
# GLOBALS
##############################################
LOG = logging.getLogger("glider.%s" % __name__)
deg = math.degrees # Tired of writing this so much

class Pilot(object):
    """
    Pilot class for translating our heading, orientation, and desired 
    coordinates into intended wing angles
    """

    def __init__(self, IMU):
        
        self.IMU = IMU
        self.threadAlive = False
        
        self.servo_range = glider_config.getfloat("flight", "servo_range")
        self.wing_flat_angle_l = glider_config.getfloat("flight", "wing_flat_angle_l")
        self.wing_flat_angle_r = glider_config.getfloat("flight", "wing_flat_angle_r")

        self.wing_angles = [self.wing_flat_angle_l, self.wing_flat_angle_r]

        self.turn_severity = glider_config.getfloat("flight", "turn_severity")
        self.desired_pitch_deg = glider_config.getfloat("flight", "desired_pitch_deg")
        self.desired_yaw = 0

        self.destination = [float(i) for i in glider_config.get("flight", "initial_destination").split(",")]
        self.location = [0,0]

    def start(self):
        pilotThread = Thread(target=self.update_wing_angles, args=())
        LOG.info("Starting up Pilot thread now")
        self.threadAlive = True
        pilotThread.start()

    def stop(self):
        self.threadAlive = False

    def scaleAbsToLimit(self, val, limit):
        """Little helper to enforce positive/negative limits"""
        sign = lambda x: (1, -1)[val < 0]
        return min(abs(val),limit) * sign(val)

    def get_desired_roll(self, yawDelta_rad):
        yawDelta_rad *= self.turn_severity 
        # The maximum amount of turning we consider for adjusting roll, is 90 degrees
        yawDelta_rad = self.scaleAbsToLimit(yawDelta_rad, math.pi/2)
        # Get the tan of the difference in heading (gentle ramp up to infinity)
        roll_angle = math.tan(yawDelta_rad)
        # Scale the tan of that angle to 1
        roll_angle= self.scaleAbsToLimit(roll_angle, 1)
        return roll_angle

    def update_wing_angles(self):
        while self.threadAlive:
            # Get the readings from the IMU
            current_pitch = self.IMU.pitch
            current_roll = self.IMU.roll
            current_yaw = self.IMU.yaw
            LOG.debug("\nCalculating wing angles")
            LOG.debug("Current P(%2.1f) R(%2.1f) Y(%2.1f)" % (
                deg(current_pitch), deg(current_roll), deg(current_yaw)))

            # Initialize the wing adjustments at 0
            # We will add up all adjustments, then scale them to the ranges of the servos.
            wing_left = 0
            wing_right = 0

            # Now adjust for pitch
            deltaPitch = math.radians(self.desired_pitch_deg) - current_pitch
            LOG.debug("Pitch Current/Desired/Delta: %2.1f/%2.1f/%2.1f" % (deg(current_pitch), self.desired_pitch_deg, deg(deltaPitch)))
            wing_left += deltaPitch # Bring both wings DOWN
            wing_right += deltaPitch # Bring both wings DOWN
            LOG.debug("Flap delta (pitched) = L(%2.1f) R(%2.1f)" % (deg(wing_left), deg(wing_right)))

            # Calculate the desired change in our heading(yaw)
            deltaYaw = self.desired_yaw - current_yaw
            deltaYaw = (deltaYaw + math.pi) % (2*math.pi) - (math.pi) # https://stackoverflow.com/a/7869457
            LOG.debug("Yaw Current/Desired: %2.2f/%2.2f" % (deg(current_yaw), deg(self.desired_yaw)))

            # Calculate the desired roll to make that happen
            desired_roll = self.get_desired_roll(deltaYaw)
            LOG.debug("Roll Current/Desired: %2.1f/%2.1f)" % (deg(current_roll), deg(desired_roll)))

            deltaRoll = desired_roll - current_roll # This is radians
            wing_left += deltaRoll
            wing_right -= deltaRoll
            LOG.debug("Flap delta (rolled) = L(%2.1f) R(%2.1f)" % (deg(wing_left), deg(wing_right)))

            # Find how much we're trying to change the flap angles, then scale to fit that change
            maxAngle = max(math.fabs(wing_left), math.fabs(wing_right))
            # Copy the wing angles so we don't modify the values in place
            wing_left_scaled = wing_left
            wing_right_scaled = wing_right
            # Scale the angles now to not exceed the max servo range
            max_servo_range_radians = math.radians(self.servo_range)
            if maxAngle > max_servo_range_radians:
                angleScale = maxAngle/max_servo_range_radians
                wing_left_scaled /= angleScale
                wing_right_scaled /= angleScale
            LOG.debug("Scaled flap delta = L(%2.1f) R(%2.1f)" % (deg(wing_left_scaled), deg(wing_right_scaled)))

            # Calculate servo degrees
            self.wing_angles = [
                self.wing_flat_angle_l + deg(wing_left_scaled),
                self.wing_flat_angle_r + deg(wing_right_scaled),
            ]

            # Log the update and sleep for the wing calc interval
            LOG.debug("Wing Angles: %02.1f %02.1f" % (self.wing_angles[0], self.wing_angles[1]))
            return self.wing_angles

    def update_destination(self, lat, lon):
        """Method to enforce that the heading is updated when current location is updated"""
        self.destination = [float(lat), float(lon)]
        self.update_desired_heading()

    def update_location(self, lat, lon):
        """Method to enforce that the heading is updated when current location is updated"""
        self.location = [lat, lon]
        self.update_desired_heading()

    def update_desired_heading(self):
        # http://stackoverflow.com/questions/4913349/haversine-formula-in-python-bearing-and-distance-between-two-gps-points
        x1, y1 = float(self.location[0]), float(self.location[1])
        x2, y2 = float(self.destination[0]), float(self.destination[1])
        LOG.warning("X1 %s Y2 %s" % (x1, y1))
        LOG.warning("X2 %s Y2 %s" % (x2, y2))
        all_coord = [x1, x2, y1, y2]
        if None in all_coord or min([abs(x) for x in all_coord]) == 0:
            LOG.warning("Some coordinates are blank/0")
            return
        # Convert gps coordinates to radian degrees
        lon1, lat1, lon2, lat2 = map(math.radians, [y1, x1, y2, x2])
        bearing = math.atan2(
            math.sin(lon2-lon1) * math.cos(lat2), 
            math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(lon2-lon1)
        )
        bearing = (bearing + (2*math.pi)) % (2*math.pi)
        LOG.warning("ANG %s" % deg(bearing))
        self.desired_yaw = bearing
