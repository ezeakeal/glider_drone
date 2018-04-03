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

        self.flap_angle_scales = {'rudder': None, 'rear': None,
                            'left_near': None, 'right_near': None,
                            'left_far': None, 'right_far': None}
        self._center_all_flaps()
        self.use_near_wing_flaps = glider_config.getboolean("flight", "use_near_wing_flaps")
        self.use_far_wing_flaps = glider_config.getboolean("flight", "use_far_wing_flaps")
        self.turn_multiplier = glider_config.getfloat("flight", "turn_severity")
        self.pitch_correction_multiplier = 1.2 # glider_config.getfloat("flight", "turn_severity")
        # Automatic pitch adjustment relative to speed
        self.nominal_pitch_deg = glider_config.getfloat("flight", "nominal_pitch_deg")
        self.pitch_critical_ground_speed = glider_config.getfloat("flight", "pitch_critical_ground_speed")
        self.pitch_nominal_ground_speed = glider_config.getfloat("flight", "pitch_nominal_ground_speed")
        self.desired_pitch_deg = self.nominal_pitch_deg

        # Current GPS destination
        self.destination = [float(i) for i in glider_config.get("flight", "initial_destination").split(",")]

    def _center_all_flaps(self):
        for flap in self.flap_angle_scales.keys():
            self.flap_angle_scales[flap] = 0.5
        return self.flap_angle_scales

    def _scaleAbsToLimit(self, val, limit):
        """Ensure -limit < val < limit"""
        return val * 1/abs(limit)

    def convert_angle_to_scale(self, angle, min=-math.pi, max=math.pi, scale_func=None, degrees=False):
        # Converts an input angle to a scale between 0 and 1 (0.5 means flatten flap)
        if degrees:
            angle = rad(angle)
        if angle < min:
            LOG.warning("Input scaling angle is less than min (%s)!" % angle)
            angle = min
        if angle > max:
            LOG.warning("Input scaling angle is greater than max (%s)!" % angle)
            angle = max
        a = (angle - min)
        init_scale = a/(max-min)
        if scale_func:
            return scale_func(init_scale)
        else:
            return init_scale

    def update_flap_angles(self):
        # Get the readings from the IMU
        current_pitch = self.IMU.pitch
        current_roll = self.IMU.roll
        current_yaw = self.IMU.yaw
        LOG.debug("\nCalculating wing angles")
        LOG.debug("Current P(%2.1f) R(%2.1f) Y(%2.1f)" % (
            deg(current_pitch), deg(current_roll), deg(current_yaw)))

        #---- Rear Flap ----
        delta_pitch = math.radians(self.desired_pitch_deg) - current_pitch
        rear_flap = self.convert_angle_to_scale(delta_pitch * self.pitch_correction_multiplier,
                                                min=rad(-45), max=rad(45)) # Rear flap adjust

        #---- Rudder ----
        delta_yaw = self.desired_yaw - current_yaw
        delta_yaw = (delta_yaw + math.pi) % (2*math.pi) - (math.pi) # https://stackoverflow.com/a/7869457
        rudder = self.convert_angle_to_scale(delta_yaw * self.turn_multiplier)

        #---- Wing Roll ----
        desired_roll = self._scaleAbsToLimit(delta_yaw * self.turn_multiplier, rad(45)) # abs(a) < 45
        delta_roll = self.convert_angle_to_scale(desired_roll - current_roll)
        wing_left = 1-delta_roll
        wing_right = delta_roll

        # Calculate servo degrees
        if self.use_near_wing_flaps:
            self.flap_angle_scales['left_near'] = wing_left
            self.flap_angle_scales['right_near'] = wing_right
        if self.use_far_wing_flaps:
            self.flap_angle_scales['left_far'] = wing_left
            self.flap_angle_scales['right_far'] = wing_right
        self.flap_angle_scales['rear'] = rear_flap
        self.flap_angle_scales['rudder'] = rudder

        # Log the update and sleep for the wing calc interval
        LOG.info("Wing Scales: %s" % json.dumps(self.flap_angle_scales, indent=2))
        return self.flap_angle_scales

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
