import math
import time
import logging
import subprocess
import RPi.GPIO as GPIO

from config import glider_config
LOG = logging.getLogger("glider.states")


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
# -----------------------------------
#         Packaging
# -----------------------------------
class packaging(gliderState):
    def __init__(self):
        super(packaging, self).__init__()
        self.nextState = "HEALTH_CHECK"
        self.sleepTime = 5

    def execute(self, glider_instance):
        self.wing_test(glider_instance)
        self.prepare_release(glider_instance)
        self.prepare_parachute(glider_instance)
        self.readyToSwitch = True

    def prepare_release(self, glider_instance):
        glider_instance.speak("Prepare Release Rod")
        time.sleep(2)
        glider_instance.speak("Open in 3 seconds")
        time.sleep(4)
        glider_instance.pwm_controller.release_from_balloon()
        glider_instance.speak("Close in 3 seconds")
        time.sleep(4)
        glider_instance.pwm_controller.release_from_balloon(reset=True)

    def prepare_parachute(self, glider_instance):
        glider_instance.speak("Prepare Parachute")
        time.sleep(2)
        glider_instance.speak("Open in 3 seconds")
        time.sleep(4)
        glider_instance.pwm_controller.release_parachute()
        glider_instance.speak("Close in 20 seconds")
        time.sleep(21)
        glider_instance.pwm_controller.release_parachute(reset=True)

    def wing_test(self, glider_instance):
        glider_instance.speak("Wing test")
        time.sleep(1)
        for scale in [0.5, 0, 0.5, 1, 0.5]:
            glider_instance.speak("Scale %s" % scale)
            time.sleep(1)
            glider_instance.pwm_controller.set_flap_scales({
                'left_near': scale, 'right_near': scale,
                'left_far': scale, 'right_far': scale
            })
        time.sleep(1)

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
        max_error = max(location.epx, location.epy)
        locationLocked = max_error < 50
        # Get battery data. Figure if healthy
        if not locationLocked:
            glider_instance.speak("Waiting for GPS")
            LOG.warning("Location is not locked yet (max error = %s)" % max_error)
        else:
            # Seems all is good
            LOG.info("Health Check Passed")
            glider_instance.telemetry_handler.set_message("Health Good")
            self.readyToSwitch = True

#-----------------------------------
#         Ascent
#-----------------------------------
class ascent(gliderState):
    def __init__(self):
        super(ascent, self)\
            .__init__()
        self.sleepTime = 10
        self.desiredAltitude = glider_config.getfloat("mission", "balloon_release_altitude")
        self.wingWiggleHeight = glider_config.getfloat("mission", "wing_antifreeze_wiggle_altitude")
        self.nextState = "RELEASE"
        self.location = None

    def execute(self, glider_instance):
        LOG.info("ASCENDING!")
        self.location = glider_instance.gps.data

    def switch(self):
        LOG.info("Checking alt (%s) > target (%s)" % (
            self.location.alt, self.desiredAltitude
        ))
        if type(self.location.alt) == float and self.location.alt > self.desiredAltitude:
            self.readyToSwitch = True
        return super(ascent, self).switch()
        
#-----------------------------------
#         Release
#-----------------------------------
class release(gliderState):
    def __init__(self):
        super(release, self).__init__()
        self.nextState = "FLIGHT"
        self.song_cmd = ["mpg321", "/opt/glider/release_song.mp3", "-q"]
        self.releaseDelay = 144

    def execute(self, glider_instance):
        LOG.info("Playing song")
        glider_instance.camera.take_video(300)
        song = subprocess.Popen(self.song_cmd)
        time.sleep(self.releaseDelay)
        LOG.info("Releasing cable")
        glider_instance.pwm_controller.release_from_balloon()
        time.sleep(5)
        song.kill()
        self.readyToSwitch = True

#-----------------------------------
#         Guided Flight
#-----------------------------------
class glide(gliderState):
    def __init__(self):
        super(glide, self).__init__()
        self.nextState = "PARACHUTE"
        self.parachute_height = glider_config.getfloat("mission", "parachute_height")
        self.location = None
        self.sleepTime = glider_config.getfloat("flight", "wing_update_interval")
        self.recalculation_timestamp_location = 0 # Counter to reduce CPU load
        self.recalculation_interval_location = glider_config.getfloat("flight", "location_refresh_interval")

    def execute(self, glider_instance):
        now = time.time()

        # Check if we need to recalculate a bearing to our destination
        if now - self.recalculation_timestamp_location > self.recalculation_interval_location :
            self.recalculation_timestamp_location = now
            self.location = glider_instance.gps.data # Get our new location
            if self.location.lat == "n/a": # Ensure that the latitude is a value before continuing
                LOG.error("Bad location, course unchanged")
            elif self.location.track == "0.0" or self.location.speed < 10: # Check that we have a heading and speed
                LOG.error("Bad heading or speed too low, orientation uncorrected (track:%s)" % self.location.track)
            else:
                glider_instance.imu.correct_heading(self.location.track)
                glider_instance.pilot.update_location(self.location.lat, self.location.lon) # Update the desired heading

        # Update the desired pitch relative to current speed (GPS)
        glider_instance.pilot.scale_pitch_for_speed(self.location.speed)
        # Update the servos
        flap_scale_dict = glider_instance.pilot.update_flap_angles()
        # Set the flaps to the flap_angle_dict
        glider_instance.pwm_controller.set_flap_scales(flap_scale_dict)
        # Check if we're ready to switch
        if (self.location and self.location.alt and type(self.location.alt) == float and self.location.alt < self.parachute_height):
            self.readyToSwitch = True

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
        glider_instance.camera.take_video(60)
        glider_instance.pilot.desired_pitch_deg = -80
        if self.chute_delay < 1:
            glider_instance.pwm_controller.release_parachute()
        flap_scale_dict = glider_instance.pilot._center_all_flaps()
        glider_instance.pwm_controller.set_flap_scales(flap_scale_dict)
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
        self.siren_duration = glider_config.getint("mission", "siren_duration")
        self.siren_pin = glider_config.getint("mission", "siren_pin")
        self.setup_siren()

    def setup_siren(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.siren_pin, GPIO.OUT)

    def execute(self, glider_instance):
        GPIO.output(self.siren_pin, GPIO.HIGH)
        time.sleep(self.siren_duration)
        GPIO.output(self.siren_pin, GPIO.LOW)
        time.sleep(3)
        for i in range(3):
            glider_instance.speak("Please help me! Contact %s" % self.contact_detail)
            time.sleep(10)
        glider_instance.speak("Disconnect the Green Blue exposed jumper leads to silence alarm")
        time.sleep(10)

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
        self.readyToSwitch = True

#-----------------------------------
#         TESTING STATES
#-----------------------------------
class test_chute(gliderState):

    def __init__(self):
        super(test_chute, self).__init__()
        self.nextState = "RECOVER"
        self.sleepTime = glider_config.getfloat("flight", "wing_update_interval")
        self.chute_deploy_delay = glider_config.getfloat("test_chute", "chute_delay_time")
        self.deploy_init_timestamp = None
        self.spoken_integer = -1

    def execute(self, glider_instance):
        now = time.time()
        if not self.deploy_init_timestamp:
            self.readyToSwitch = False
            glider_instance.pwm_controller.release_parachute(reset=True)
            glider_instance.speak("Parachute test")
            try:
                glider_instance.camera.take_video(20)
            except:
                LOG.exception("Camera not working")
            self.deploy_init_timestamp = now

        # We don't want to turn, just want to keep flat.
        flap_scale_dict = glider_instance.pilot._center_all_flaps()
        glider_instance.pwm_controller.set_flap_scales(flap_scale_dict)

        # Convert the times to a countdown
        delay_sec = int(math.ceil(self.chute_deploy_delay - (now - self.deploy_init_timestamp)))
        if delay_sec != self.spoken_integer:
            glider_instance.speak(str(delay_sec))
        self.spoken_integer = delay_sec

        # Check if we're ready to switch
        if (now - self.deploy_init_timestamp > self.chute_deploy_delay):
            glider_instance.pwm_controller.release_parachute()
            self.readyToSwitch = True
            # Reset the state to be able to run the test twice
            self.spoken_integer = -1
            self.deploy_init_timestamp = None

class test_release(gliderState):

    def __init__(self):
        super(test_release, self).__init__()
        self.nextState = "RECOVER"
        self.sleepTime = glider_config.getfloat("flight", "wing_update_interval")
        self.deploy_delay = glider_config.getfloat("test_release", "release_delay_time")
        self.deploy_init_timestamp = None
        self.spoken_integer = -1

    def execute(self, glider_instance):
        now = time.time()
        if not self.deploy_init_timestamp:
            self.readyToSwitch = False
            glider_instance.pwm_controller.release_from_balloon(reset=True)
            glider_instance.speak("Release test")
            try:
                glider_instance.camera.take_video(10)
            except:
                LOG.exception("Camera not working")
            self.deploy_init_timestamp = now

        # Convert the times to a countdown
        delay_sec = int(math.ceil(self.deploy_delay - (now - self.deploy_init_timestamp)))
        if delay_sec != self.spoken_integer:
            glider_instance.speak(str(delay_sec))
        self.spoken_integer = delay_sec

        # Check if we're ready to switch
        if (now - self.deploy_init_timestamp > self.deploy_delay):
            glider_instance.pwm_controller.release_from_balloon()
            self.readyToSwitch = True
            # Reset the state to be able to run the test twice
            self.spoken_integer = -1
            self.deploy_init_timestamp = None
