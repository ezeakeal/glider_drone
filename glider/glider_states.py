import math
import time
import logging
import subprocess

from config import glider_config
LOG = logging.getLogger('state')


##########################################
# BASE STATE CLASS
##########################################
class gliderState(object):
    """
    This is a base class which enforces an execute
    and switch method
    """
    def __init__(self):
        self.readyToSwitch = False
        self.nextState = None
        self.exitState = ""
        self.sleepTime = 1 # How long to sleep between execute() calls

    def rest(self):
        time.sleep(self.sleepTime)

    def execute(self, glider_instance):
        raise NotImplementedError("Execute function is required")

    def switch(self):
        LOG.info("Next state: %s" % self.nextState)
        if not self.nextState:
            raise Exception("NextState not defined")
        if self.readyToSwitch:
            return self.nextState
        else:
            return None

##########################################
# CLASSES - STATE
##########################################
#-----------------------------------
#         Health Check
#-----------------------------------
class healthCheck(gliderState):
    def __init__(self):
        super(healthCheck, self).__init__()
        self.nextState = "ASCENT"
        self.sleepTime = 5

    def execute(self, glider_instance):
        # Get the location data, figure if locked
        location = glider_instance.gps.data
        locationLocked = (location.epx < 20 and location.epy < 20)
        # Get battery data. Figure if healthy
        if not locationLocked:
            LOG.warning("Location is not locked yet")
        else:
            # Seems all is good
            LOG.info("Health Check Passed")
            glider_instance.speak("Health Check Complete")
            glider_instance.telemetry_handler.set_message("Health Good")
            self.readyToSwitch = True

#-----------------------------------
#         Ascent
#-----------------------------------
class ascent(gliderState):
    def __init__(self):
        super(ascent, self).__init__()
        self.sleepTime = 5
        self.desiredAltitude = glider_config.getfloat("mission", "balloon_release_altitude")
        self.nextState = "RELEASE"
        self.wing_angle_acc = 0
        self.location = None
        self.wing_flat_angle_l = glider_config.getfloat("flight", "wing_flat_angle_l")
        self.wing_flat_angle_r = glider_config.getfloat("flight", "wing_flat_angle_r")

    def execute(self, glider_instance):
        LOG.info("ASCENDING!")
        self.location = glider_instance.gps.data
        # Keep moving the wings to stop grease freezing in servos
        # wing_angle_acc is an incremented counter which is used to sweep the wing angles back and forth over 10 deg
        self.wing_angle_acc += .2
        wing_angles = [
            self.wing_flat_angle_l + 10*math.cos(self.wing_angle_acc),
            self.wing_flat_angle_r + 10*math.cos(self.wing_angle_acc)
        ]
        LOG.info("Setting wing angles: %s" % wing_angles)
        glider_instance.pwm_controller.set_wings(wing_angles[0], wing_angles[1])

    def switch(self):
        LOG.info("Checking alt (%s) > target (%s)" % (
            self.location.alt, self.desiredAltitude
        ))
        if self.location.alt > self.desiredAltitude:
            self.readyToSwitch = True
        return super(ascent, self).switch()
        
#-----------------------------------
#         Release
#-----------------------------------
class release(gliderState):
    def __init__(self):
        super(release, self).__init__()
        self.nextState = "FLIGHT"
        self.song_cmd = ["play", "-v 1.0", "/opt/glider/release_song.mp3", "-q"]
        self.releaseDelay = 145

    def execute(self, glider_instance):
        LOG.info("Playing song")
        song = subprocess.Popen(self.song_cmd)
        time.sleep(self.releaseDelay)
        LOG.info("Releasing cable")
        glider_instance.pwm_controller.release_from_balloon()
        time.sleep(5)
        song.kill()

    def switch(self):
        self.readyToSwitch = True
        return super(release, self).switch()
    
#-----------------------------------
#         Guided Flight
#-----------------------------------
class glide(gliderState):
    def __init__(self):
        super(glide, self).__init__()
        self.nextState = "PARACHUTE"
        self.parachute_height = glider_config.get("mission", "parachute_height")
        self.location = None
        self.sleepTime = glider_config.getfloat("flight", "wing_update_interval")
        self.recalculate_iter = 0 # Counter to reduce CPU load (recalculate
        self.recalculation_interval= glider_config.get("flight", "location_refresh_interval")

    def execute(self, glider_instance):
        now = time.time()
        if now - self.recalculation_timestamp > self.recalculation_interval:
            self.recalculation_timestamp = now
            # Get our new location
            self.location = glider_instance.gps.data
            glider_instance.pilot.update_location(self.location.lat, self.location.lon)
        # Update the servos
        left_angle, right_angle = glider_instance.pilot.update_wing_angles()
        glider_instance.pwm_controller.set_wings(left_angle, right_angle)

    def switch(self):
        if (self.location and
            self.location.alt and
            (not math.isnan(self.location.alt)) and
            self.location.altitude < self.parachute_height):
            self.readyToSwitch = True
        return super(glide, self).switch()

#-----------------------------------
#         PARACHUTE
#-----------------------------------
class parachute(gliderState):
    def __init__(self):
        super(parachute, self).__init__()
        self.nextState = "RECOVER"
        self.sleepTime = glider_config.getfloat("flight", "wing_update_interval")
        self.chute_delay = glider_config.getfloat("mission", "dive_time_before_chute")

    def execute(self, glider_instance):
        glider_instance.pilot.desired_pitch_deg(-80)
        glider_instance.speak("Releasing parachute!")
        glider_instance.updateWingAngles()
        if self.chute_delay < 1:
            glider_instance.pwm_controller.release_parachute()
        self.chute_delay -= 1

    def switch(self):
        if self.chute_delay < 0:
            self.readyToSwitch = True
        return super(parachute, self).switch()


#-----------------------------------
#         WAIT FOR RECOVERY
#-----------------------------------
class recovery(gliderState):
    def __init__(self):
        super(recovery, self).__init__()
        self.nextState = "RECOVER"
        self.sleepTime = 15
        self.contact_detail = glider_config.get("mission", "contact_detail")

    def execute(self, glider_instance):
        glider_instance.speak("Please help me! Contact %s" )

    def switch(self):
        pass


#-----------------------------------
#         EMERGENCY
#-----------------------------------
class errorState(gliderState):
    def __init__(self):
        super(errorState, self).__init__()
        self.nextState = "PARACHUTE"

    def execute(self, glider_instance):
        # Send data over radio.
        # Tell people there is something wrong
        # Send location, orientation
        # Send states of parachute/release motor
        # Send battery level
        # LOOK FOR A RESPONSE!
        # We need to set the state it should go in to..
        pass

    def switch(self):
        pass
