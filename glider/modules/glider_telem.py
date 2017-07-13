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
import dateutil.parser
from threading import Thread
from . import glider_config

##########################################
# GLOBALS
##########################################
LOG = logging.getLogger("Telemetry")


class TelemetryHandler():
    """Telemetry builder.

    Because this is run in the background periodically, it needs access
    to the glider modules (like IMU, GPS). Have to give that on init()
    unfortunately.
    """
    def __init__(self, radio, imu, pilot, gps):
        self.threadAlive = True

        self.radio = radio
        self.imu = imu
        self.pilot = pilot
        self.gps = gps
        self.glider_state = None
        self.alien_gps_dump = {}

        self.glider_data_lastsent = time.time()
        self.telemetry_lastsent = time.time()
        self.aliendatadump_lastsent = time.time()

        self.glider_data_interval = glider_config.getint("telemetry", "interval_data")
        self.telemetry_interval = glider_config.getint("telemetry", "interval_telem")
        self.aliendatadump_interval = glider_config.getint("telemetry", "interval_aliendump")

    def genTelemStr_orientation(self):
        telStr = "O:%2.1f_%2.1f_%2.1f" % (
            math.degrees(self.imu.roll),
            math.degrees(self.imu.pitch),
            math.degrees(self.imu.yaw))
        return telStr

    def genTelemStr_wing(self):
        telStr = "W:%2.1f_%2.1f" % (
            self.pilot.wing_param['left']['current'],
            self.pilot.wing_param['right']['current'])
        return telStr

    def send_glider_data(self):
        LOG.debug("Sending glider data")
        data = [
            self.genTelemStr_orientation(), 
            self.genTelemStr_wing(), 
            "S:%s" % self.glider_state
        ]
        self.radio.send_data(data)

    def send_telemetry(self):
        LOG.debug("Sending glider telemetry")
        gps_fix = self.gps.getFix()
        hhmmss = int(time.strftime("%H%M%S"))
        if gps_fix:
            try:
                hhmmss = int(dateutil.parser.parse(self.gps.gpsd.utc).strftime("%H%M%S"))
            except:
                LOG.warning("Can't generate gps telemetry")
        lon_dec_deg, lat_dec_deg = self.gps.getLonLatDeg()
        alt = gps_fix.altitude
        lat_dil = gps_fix.epx
        if math.isnan(lat_dil):
            lat_dil = 99.99
        if math.isnan(alt):
            alt = 0
        temp1 = 0
        temp2 = 0
        pressure = 0
        self.radio.send_telem(hhmmss, lat_dec_deg, lon_dec_deg, lat_dil, alt, temp1, temp2, pressure)

    def send_aliendatadump(self):
        LOG.info("Echoing %s telemetry packets" % len(self.alien_gps_dump.keys()))
        for callsign, telemtry_packet in self.alien_gps_dump.items():
            LOG.info("Echoing %s telemetry packets" % callsign)
            self.radio.send_packet(telemtry_packet, mode=self.radio.MODE_P2MP)
            time.sleep(0.5)

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
                if now - self.aliendatadump_lastsent > self.aliendatadump_interval:
                    self.send_aliendatadump()
                    self.aliendatadump_lastsent = now
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
