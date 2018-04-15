##############################################
#
# GliderV3 Client Software
# Author: Daniel Vagg
#
##############################################
import time
import math
import logging
import traceback
deg = math.degrees

import datetime
import dateutil.parser
from threading import Thread
from . import glider_config

##########################################
# GLOBALS
##########################################
LOG = logging.getLogger("glider.%s" % __name__)


class TelemetryHandler():
    """Telemetry builder.

    Because this is run in the background periodically, it needs access
    to the glider modules (like IMU, GPS). Have to give that on init()
    unfortunately.
    """
    def __init__(self, radio, imu, pilot, gps, glider):
        self.threadAlive = True

        self.radio = radio
        self.imu = imu
        self.pilot = pilot
        self.gps = gps
        self.glider = glider
        self.glider_state = None
        self.alien_gps_dump = {}

        self.glider_data_lastsent = time.time()
        self.telemetry_lastsent = time.time()
        self.aliendatadump_lastsent = time.time()

        self.glider_data_interval = glider_config.getfloat("telemetry", "interval_data")
        self.telemetry_interval = glider_config.getfloat("telemetry", "interval_telem")

    def send_glider_data(self):
        LOG.debug("Sending glider data")
        data = [
            "O:%2.1f_%2.1f_%2.1f" % (deg(self.imu.roll), deg(self.imu.pitch), deg(self.imu.yaw)),
            "W:%s" % ("_".join(["%1.2f" % float(x) for x in self.pilot.flap_angle_scales.values()])),
            "H:%s_%s" % (deg(self.pilot.desired_yaw), self.pilot.desired_pitch_deg),
            "G:%s_%s" % (self.gps.data.speed, self.gps.data.track),
            "C:%s_%s" % (self.glider.commands_received, self.glider.last_command_dir),
        ]
        self.radio.send_data(data)

    def send_telemetry(self):
        LOG.debug("Sending glider telemetry")
        location_data = self.gps.data
        hhmmss = datetime.datetime.now()
        try:
            hhmmss = dateutil.parser.parse(location_data.time)
        except:
            LOG.warning("Can't generate gps telemetry - no time fix")
        self.radio.send_telem(
            hhmmss,
            location_data.lat, location_data.lon,
            location_data.epx, location_data.alt,
            self.pilot.destination[0], self.pilot.destination[1],
            self.glider.current_state
        )

    def set_state(self, state):
        self.glider_state = state

    def set_message(self, message):
        self.radio.send_data(["M:%s" % message])

    def telemLoop(self):
        while self.threadAlive:
            try:
                now = time.time()
                if now - self.glider_data_lastsent > self.glider_data_interval:
                    self.send_glider_data()
                    self.glider_data_lastsent = now
                if now - self.telemetry_lastsent > self.telemetry_interval:
                    self.send_telemetry()
                    self.telemetry_lastsent = now
            except:
                LOG.error(traceback.format_exc())
            time.sleep(0.1)

    def start(self):
        LOG.info("Starting Telemetry thread")
        threadT = Thread(target=self.telemLoop, args=())
        self.threadAlive = True
        threadT.start()

    def stop(self):
        self.threadAlive = False

#---------- END CLASS -------------
