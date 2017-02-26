import os
import log
import math
import time
import numpy
import logging
import subprocess

# Glider Imports
import glider_lib
import glider_schedule as schedule
import glider_states as states

from glider.settings import *


##########################################
# GLOBALS
##########################################
LOG = setup_custom_logger('state')

##########################################
# FUNCTIONS - UTIL
##########################################
def setState(newState):
    """Sets the global state which is used for various updates"""
    global STATE
    if getattr(states, newState):
        STATE = newState
    else:
        raise Exception("State (%s) does not exist" % newState)


def scheduleRelease():
    global CURRENT_STATE
    CURRENT_STATE = "release"


##########################################
# CLASSES - BASE
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
        self.sleepTime = 1

    def rest(self):
        time.sleep(self.sleepTime)

    def execute(self):
        raise NotImplementedError("Execute function is required")

    def switch(self):
        LOG.info("Next state: %s" % self.nextState)
        if not self.nextState:
            raise Exception("NextState not defined")
        if self.readyToSwitch:
            glider_lib.speak("Switching state to %s" % self.nextState)
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
        self.checkedWings = False
        self.sleepTime = 5

    def execute(self):
        glider_lib.center_wings()
        if not self.checkedWings:
            self.wingCheck()
        # Get the location data, figure if locked
        location = glider_lib.GPS.getFix()
        locationLocked = (location.epx < 20 and location.epy < 20)
        # Get battery data. Figure if healthy
        if not locationLocked:
            LOG.warning("Location is not locked yet")
        else:
            # Seems all is good
            LOG.info("Health Check Passed")
            glider_lib.speak("Health Check Complete")
            glider_lib.TELEM.set_message("Health Good")
            self.readyToSwitch = True
    
    def wingCheck(self):
        LOG.info("Moving wings")
        wingMoveInterval = 0.2
        # Move the wings to max range
        glider_lib.center_wings()
        time.sleep(wingMoveInterval)
        glider_lib.min_wings()
        time.sleep(wingMoveInterval)
        glider_lib.center_wings()
        time.sleep(wingMoveInterval)
        glider_lib.max_wings()
        time.sleep(wingMoveInterval)
        glider_lib.center_wings()
        self.checkedWings = True

#-----------------------------------
#         Ascent
#-----------------------------------
class ascent(gliderState):
    def __init__(self):
        super(ascent, self).__init__()
        self.sleepTime = 5
        self.desiredAltitude = 22000
        self.nextState = "RELEASE"
        self.wing_angle_acc = 0

    def execute(self):
        LOG.info("ASCENDING!")
        # Keep moving the wings to stop grease freezing in servos
        self.wing_angle_acc += .2
        wing_angles = [
            90 + 10*math.cos(self.wing_angle_acc),
            96 + 10*math.cos(self.wing_angle_acc)
        ]
        LOG.info("Setting wing angles: %s" % wing_angles)
        glider_lib.setWingAngle(wing_angles)

    def switch(self):
        location = glider_lib.GPS.getFix()
        LOG.info("Checking alt (%s) > target (%s)" % (
            location.altitude, self.desiredAltitude
        ))
        if location.altitude > self.desiredAltitude:
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

    def execute(self):
        LOG.info("Playing song")
        song = subprocess.Popen(self.song_cmd)
        time.sleep(self.releaseDelay)
        LOG.info("Releasing cable")
        glider_lib.releaseChord()
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
        self.parachute_height = 2000
        self.location = None
        self.sleepTime = 0.02
        self.recalculate_iter = 0 # Counter to reduce CPU load
        self.recalculate_iter_delay = 30 # Update every 20 or so seconds

    def execute(self):
        if self.recalculate_iter == 0:
            self.recalculate_iter = self.recalculate_iter_delay
            # Get our new location
            LOG.debug("Figuring out location")
            self.location = glider_lib.GPS.getFix()
            LOG.debug("Current Location: \nLAT:%s LON:%s ALT:%s" % (
                self.location.latitude, self.location.longitude, self.location.altitude
            ))
            LOG.debug("Target Location: \nLAT:%s LON:%s" % (
                glider_lib.PILOT.destination[0], glider_lib.PILOT.destination[1]
            ))
            # Update the pilot
            glider_lib.PILOT.updateLocation(self.location.latitude, self.location.longitude)
            # Get pilot to update bearing
            glider_lib.PILOT.updateDesiredYaw()
        # Update the servos
        LOG.debug("Updating angles (%s)" % self.recalculate_iter)
        glider_lib.updateWingAngles()
        self.recalculate_iter -= 1

        
    def switch(self):
        if (self.location and self.location.altitude and 
            (not math.isnan(self.location.altitude)) and
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
        self.sleepTime = 0.02
        self.chute_delay = 5 * (1/self.sleepTime) # 15 seconds

    def execute(self):
        glider_lib.setPitchAngle(-80)
        glider_lib.speak("Releasing parachute!")
        glider_lib.updateWingAngles()
        if self.chute_delay < 1:
            glider_lib.releaseParachute()
        self.chute_delay -= 1

    def switch(self):
        if self.chute_delay < 0:
            self.readyToSwitch = True
        return super(parachute, self).switch()


#-----------------------------------
#         EMERGENCY
#-----------------------------------
class recovery(gliderState):
    def __init__(self):
        super(recovery, self).__init__()
        self.nextState = "RECOVER"
        self.sleepTime = 15

    def execute(self):
        glider_lib.speak("Help me")
        LOG.critical("Attempting Recovery")

    def switch(self):
        pass


#-----------------------------------
#         EMERGENCY
#-----------------------------------
class errorState(gliderState):
    def __init__(self):
        super(errorState, self).__init__()
        self.nextState = "PARACHUTE"

    def execute(self):
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
