import glob
import os
import logging
import logging.config
import subprocess
import traceback

##########################################
# Configure logging
##########################################
base_dir = os.path.dirname(__file__)
conf_path = os.path.join(base_dir, "glider_conf.ini")
logging.config.fileConfig(conf_path)

LOG = logging.getLogger("glider")
logging.getLogger("Adafruit_I2C").setLevel(logging.WARN)

#########################################
# Import glider modules and states
#########################################
from modules.glider_gps import GPS
from modules.glider_camera import GliderCamera
from modules.glider_imu import IMU
from modules.glider_pilot import Pilot
from modules.glider_pwm_controller import GliderPWMController
from modules.glider_radio import GliderRadio
from modules.glider_telem import TelemetryHandler

import glider_states as gstates

#
#     #####################################################################
#     # FUNCTIONS - Audio/Video
#     #####################################################################
#
#
#
#     def sendImage():
#         newest_image = max(glob.iglob('%s/low_*.jpg' % CAMERA.photo_path), key=os.path.getctime)
#         RADIO.sendImage(newest_image)
#
#
#
#     ########################
#     # Alien Telemetry
#     ########################
#     def storeAlienTelemetry(telemetry_string, callsign):
#         LOG.debug("Storing Alien Telemetry for %s: (%s)" % (callsign, telemetry_string))
#         TELEM.alien_gps_dump[callsign] = telemetry_string

##########################################
# MAIN
##########################################
class GliderCommandMixin(object):
    COMMAND_DIRECTIVES = None

    def __init__(self):
        self.COMMAND_DIRECTIVES = {
            "PA": self.pitch_change,
            "O": self.state_change,
            "TS": self.turn_severity_change,
            "DEST": self.destination_change,
            "IMAGE": self.image_command,
        }

    def command_handler(self, msg_dict, **kwargs):
        LOG.info("Handling command: %s %s" % (msg_dict, kwargs))
        command_data = msg_dict['message']
        command_parts = command_data.split("|")
        command_instruction = command_parts[0]
        command_function = self.COMMAND_DIRECTIVES.get(command_instruction)
        if not command_function:
            LOG.error("No command found for instruction: %s" % command_instruction)
        try:
            return command_function(command_parts)
        except:
            LOG.exception("Error in running command")
            return None

    def pitch_change(self, arg_array):
        new_pitch = float(arg_array[1])
        if new_pitch < 0 and new_pitch > -90:
            self.pilot.desired_pitch_deg = new_pitch
        else:
            LOG.error("Bad pitch (Not between 0 and -90): %s" % new_pitch)

    def state_change(self, arg_array):
        new_state = arg_array[1]
        if new_state in self.state_machine.keys():
            self.current_state = new_state
        else:
            LOG.error("Bad state requested: %s" % new_state)

    def turn_severity_change(self, arg_array):
        new_severity = float(arg_array[1])
        if new_severity > 0 and new_severity < 3:
            self.pilot.turn_severity = new_severity
        else:
            LOG.error("Bad severity (Not between 0 and 3): %s" % new_severity)

    def destination_change(self, arg_array):
        lat = arg_array[1]
        lon = arg_array[2]
        self.pilot.update_destination(arg_array[1], arg_array[2])

    def image_command(self, arg_array):
        newest_image = max(glob.iglob('%s/low_*.jpg' % self.camera.photo_path), key=os.path.getctime)
        self.radio.sendImage(newest_image)


class Glider(GliderCommandMixin):
    state_machine = {
        "HEALTH_CHECK": gstates.healthCheck(),
        "ASCENT": gstates.ascent(),
        "RELEASE": gstates.release(),
        "FLIGHT": gstates.glide(),
        "PARACHUTE": gstates.parachute(),
        "RECOVER": gstates.recovery(),
        "ERROR": gstates.errorState()
    }
    current_state = "FLIGHT"

    def __init__(self):
        # Initialize all modules
        self.speak("Initializing")
        self.gps = GPS()
        self.imu = IMU()
        self.radio = GliderRadio(self.command_handler)
        self.camera = GliderCamera()
        self.pwm_controller = GliderPWMController()
        # The pilot and telemetry handler need access to the instances we created
        self.pilot = Pilot(self.imu)
        self.telemetry_handler = TelemetryHandler(self.radio, self.imu, self.pilot, self.gps, self)
        self.start_modules()
        self.speak("Glider ready")

    def start_modules(self):
        # Start up modules
        self.speak("Starting modules")
        self.gps.start()
        self.pilot.start()
        self.camera.start()
        self.telemetry_handler.start()
        self.pwm_controller.start()
        self.radio.start()

    def stop_modules(self):
        self.speak("Stopping modules")
        self.gps.stop()
        self.pilot.stop()
        self.camera.stop()
        self.telemetry_handler.stop()
        self.pwm_controller.stop()

    def stop(self):
        self.speak("Shutting down")
        self.stop_modules()

    def speak(self, text):
        LOG.info("Speaking %s" % text)
        with open(os.devnull, "w") as devnull:
            subprocess.call(["espeak", "-ven-us", "-m", "-p", "70", "-s", "180", text], stdout=devnull, stderr=devnull)

    def run_state_machine(self):
        self.running = True
        while self.running:
            try:
                LOG.debug("Current state: %s" % self.current_state)
                stateClass = self.state_machine[self.current_state]
                stateClass.rest()
                stateClass.execute(self)

                # Check if we switch
                newState = stateClass.switch()
                LOG.debug("New state: %s" % newState)

                # Switch in to new state
                if newState:
                    LOG.debug("State is changing from (%s) to (%s)" % (
                        self.current_state, newState))
                    self.speak("Switching state to %s" % newState)
                    self.current_state = newState

            except KeyboardInterrupt:
                self.stop()
                raise # Don't go to error state, close the program!
            except:
                LOG.error(traceback.print_exc())
                self.current_state = "ERROR"

if __name__ == '__main__':
    try:
        glider = Glider()
        glider.run_state_machine()
        glider.stop()
    except Exception as e:
        print traceback.print_exc()
        with open(os.devnull, "w") as devnull:
            subprocess.call(
                ["espeak", "-ven+f3", "-m", "-p", "70", "-s", "180", "Error encountered! %s" % str(e)],
                stdout=devnull, stderr=devnull
            )
