import time
import math
import json
import logging
from threading import Thread
from . import glider_config

##############################################
# GLOBALS
##############################################
LOG = logging.getLogger("glider.%s" % __name__)
deg = math.degrees # Tired of writing this so much
rad = math.radians

class Pilot(object):
    """
    Pilot class for translating our heading, orientation, and desired 
    coordinates into intended wing angles
    """

    desired_yaw = 0
    location = [0, 0]

    def __init__(self, IMU):
        
        self.IMU = IMU
        self.threadAlive = False

        self.servo_range = glider_config.getfloat("flight", "servo_range")

        self.flap_angles = {'rudder': None, 'rear': None,
                            'left_near': None, 'right_near': None,
                            'left_far': None, 'right_far': None}
        self._center_all_flaps()
        self.use_near_wing_flaps = glider_config.getboolean("flight", "use_near_wing_flaps")
        self.use_far_wing_flaps = glider_config.getboolean("flight", "use_far_wing_flaps")

        self.turn_severity = glider_config.getfloat("flight", "turn_severity")
        self.nominal_pitch_deg = glider_config.getfloat("flight", "nominal_pitch_deg")
        self.pitch_roll_response = glider_config.getfloat("flight", "pitch_roll_response")
        self.pitch_critical_ground_speed = glider_config.getfloat("flight", "pitch_critical_ground_speed")
        self.pitch_nominal_ground_speed = glider_config.getfloat("flight", "pitch_nominal_ground_speed")
        self.pitch_decay_factor = glider_config.getfloat("flight", "pitch_decay_factor")

        self.desired_pitch_deg = self.nominal_pitch_deg
        self.destination = [float(i) for i in glider_config.get("flight", "initial_destination").split(",")]

    def _center_all_flaps(self):
        for flap in self.flap_angles.keys():
            self.flap_angles[flap] = glider_config.getfloat("flight", "flap_center_%s" % flap)

    def start(self):
        pilotThread = Thread(target=self.update_flap_angles, args=())
        LOG.info("Starting up Pilot thread now")
        self.threadAlive = True
        pilotThread.start()

    def stop(self):
        self.threadAlive = False

    def _scaleAbsToLimit(self, val, limit):
        """Little helper to enforce positive/negative limits"""
        sign = lambda x: (1, -1)[val < 0]
        return min(abs(val),limit) * sign(val)

    def _get_desired_roll(self, yawDelta_rad):
        yawDelta_rad *= self.turn_severity 
        # The maximum amount of turning we consider for adjusting roll, is 90 degrees
        yawDelta_rad = self._scaleAbsToLimit(yawDelta_rad, math.pi/2)
        # Get the tan of the difference in heading (gentle ramp up to infinity)
        roll_angle = math.tan(yawDelta_rad)
        # Scale the tan of that angle to 1
        roll_angle= self._scaleAbsToLimit(roll_angle, 1)
        return roll_angle

    def update_flap_angles(self):
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
            rear_flap = 0
            rudder = 0

            # Now adjust for pitch
            deltaPitch = math.radians(self.desired_pitch_deg) - current_pitch
            LOG.debug("Pitch Current/Desired/Delta: %2.1f/%2.1f/%2.1f" % (deg(current_pitch), self.desired_pitch_deg, deg(deltaPitch)))
            rear_flap += deltaPitch # Rear flap adjust
            LOG.debug("Flap delta (pitched) = %2.1f" % (deg(rear_flap)))

            # Calculate the desired change in our heading(yaw)
            deltaYaw = self.desired_yaw - current_yaw
            deltaYaw = (deltaYaw + math.pi) % (2*math.pi) - (math.pi) # https://stackoverflow.com/a/7869457
            rudder += deltaYaw
            LOG.debug("Yaw Current/Desired: %2.2f/%2.2f" % (deg(current_yaw), deg(self.desired_yaw)))

            # Calculate the desired roll to make that happen
            desired_roll = self._get_desired_roll(deltaYaw)
            LOG.debug("Roll Current/Desired: %2.1f/%2.1f)" % (deg(current_roll), deg(desired_roll)))
            rear_flap += desired_roll * self.pitch_roll_response

            deltaRoll = desired_roll - current_roll # This is radians
            wing_left -= deltaRoll
            wing_right += deltaRoll
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

            # Now scale the rudder and rear
            for ang in [rear_flap, rudder]:
                ang_scale = math.fabs(ang)
                if ang_scale > max_servo_range_radians:
                    ang = ang_scale / max_servo_range_radians

            # Calculate servo degrees
            if self.use_far_wing_flaps:
                self.flap_angles['wing_l_f'] = deg(wing_left_scaled)
                self.flap_angles['wing_r_f'] = deg(wing_right_scaled)
            if self.use_near_wing_flaps:
                self.flap_angles['wing_l_n'] = deg(wing_left_scaled)
                self.flap_angles['wing_r_n'] = deg(wing_right_scaled)
            self.flap_angles['rear_flap'] = deg(rear_flap)
            self.flap_angles['rudder'] = deg(rudder)

            # Log the update and sleep for the wing calc interval
            LOG.debug("Wing Angles: %s" % json.dumps(self.flap_angles, indent=2))

            return self.flap_angles

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

    def scale_pitch_for_speed(self, speed_mps):
        # Speed in m/s from GPS
        critical_pitch = -45
        pos_speed_delta = max(self.pitch_critical_ground_speed, speed_mps) # bound the speed from the critical speed
        relevant_speed_delta = min(pos_speed_delta, self.pitch_nominal_ground_speed) # bound to nominal speed
        self.desired_pitch_deg = critical_pitch + (self.nominal_pitch_deg - critical_pitch) * \
                math.sin(math.pi/2 * (relevant_speed_delta/self.pitch_nominal_ground_speed))
