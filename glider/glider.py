import sys
import math
import time
import types
import signal
import logging
import traceback
import importlib

print "Starting glider.."

# Glider Imports
try:
    import glider_operations
except:
    print traceback.print_exc()
    sys.exit(1)
from glider_states import *

##########################################
# TODO
##########################################

##########################################
# GLOBALS
##########################################
LOG = setup_custom_logger('core')

STATE_MACHINE = {
    "HEALTH_CHECK"  : healthCheck(),
    "ASCENT"        : ascent(),                   
    "RELEASE"       : release(),                
    "FLIGHT"        : glide(),                    
    "PARACHUTE"     : parachute(),
    "RECOVER"       : recovery(),
    "ERROR"         : errorState()
}
CURRENT_STATE = "HEALTH_CHECK"
RUNNING = True

##########################################
# FUNCTIONS - UTIL
##########################################
def signal_handler(signal, frame):
    global RUNNING
    RUNNING = False


##########################################
# MAIN
##########################################      
def startUp():
    glider_operations.speak("Starting up")
    glider_operations.startUp()
    signal.signal(signal.SIGINT, signal_handler)


def shutDown():
    glider_operations.speak("Shutting down")
    glider_operations.shutDown()


def runGliderStateMachine():
    global CURRENT_STATE
    glider_operations.speak("Initialized")
    while RUNNING:
        try:
            LOG.debug("Current state: %s" % CURRENT_STATE)
            stateClass = STATE_MACHINE[CURRENT_STATE]
            stateClass.rest()
            stateClass.execute()
            newState = stateClass.switch()
            LOG.debug("Retrieved newState: %s" % newState)
            # Check if we need to override the state for any reason (this signal comes from groundstation)
            overrideState = glider_operations.getOverrideState()
            if overrideState:
                LOG.debug("Override state: %s" % overrideState)
                glider_operations.setOverrideState(None)
                if overrideState and overrideState in STATE_MACHINE.keys():
                    newState = overrideState
                    LOG.debug("Set override state: %s" % overrideState)
            # Switch in to new state
            LOG.debug("New state: %s" % newState)
            if newState:
                LOG.debug("State is being updated from (%s) to (%s)" % (
                    CURRENT_STATE, newState))
                CURRENT_STATE = newState
                glider_operations.set_current_state(CURRENT_STATE) # for reference (sent in telemetry)
        except:
            LOG.error(traceback.print_exc())
            CURRENT_STATE = "ERROR"


if __name__ == '__main__':
    try:
        startUp()
        runGliderStateMachine()
        shutDown()
    except:
        print traceback.print_exc()
