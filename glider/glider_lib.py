import os
import log
import math
import glob
import logging
import traceback
import subprocess

import glider_ATMegaController as controller

from glider_imu import IMU
from glider_gps import GPS_USB
from glider_pilot import Pilot
from glider_telem import TelemetryHandler
from glider_camera import GliderCamera
from glider_radio import GliderRadio

import RPi.GPIO as GPIO
# http://raspi.tv/2013/automatic-exposure-compensation-testing-for-the-pi-camera
# http://bytingidea.com/2014/12/11/raspberry-pi-powered-long-exposures/

from glider.settings import *

LOG = setup_custom_logger('lib')

data_dump = "/data/data_received.dump"
data_dump_file = None
##########################################
# FUNCTION - Received instruction!
##########################################
def dataHandler(packet):
    global OVERRIDE_STATE
    try:
        packet_type = packet['id']
        if data_dump_file:
            data_dump_file.write("%s\n")
        else:
            LOG.warning("Data dump not open yet")
        LOG.debug("Data packet (%s) recieved: %s" % (packet_type, packet))
        if packet_type == "rx":
            LOG.info("RX packet (%s) recieved: %s" % (packet_type, packet))
            packet_data = packet['rf_data']
            data_parts = packet_data.split("|")
            LOG.info("Data parts: %s" % data_parts)
            if len(data_parts) < 2:
                return
            instruct = data_parts[0]
            data = data_parts[1:]
            LOG.info("Data instruct(%s) data(%s)" % (instruct, data))
            if instruct == "O":
                setOverrideState("|".join(data))
            if instruct == "PA":
                setPitchAngle(data[0])
            if instruct == "TS":
                setTurnSeverity(data[0])
            if instruct == "DEST":
                setDestination(data[0], data[1])
            if instruct == "IMAGE":
                sendImage()
            if instruct == "T":
                storeAlienTelemetry(packet_data, data[0])
    except Exception, e:
        LOG.error(traceback.format_exc())


##########################################
# GLOBAL COMPONENTS
##########################################
##############################################
# ORIENTATION WAKE UP
# wake up
# aibpidbgpagd shake up
# shake up
# iopubadgaebadg make up
# make up
# ....
# YOU WANTED TO!
##############################################
GPS = GPS_USB()
ORIENT = IMU(GPS) # yaw should be 0 when north
CAMERA = GliderCamera()
RADIO = GliderRadio("/dev/ttyAMA0", "GliderV2", callback=dataHandler)
PILOT = Pilot(ORIENT, desired_pitch=-math.radians(30))
TELEM = TelemetryHandler(RADIO, ORIENT, PILOT, GPS)

##########################################
# GLOBALS
##########################################
OVERRIDE_STATE = None
CURRENT_STATE = None

# --- LED ---
LED_RUNNING = 11

##########################################
# FUNCTIONS - UTILITY
##########################################


def startUp():
    global data_dump_file
    LOG.info("Starting up")
    data_dump_file = open(data_dump, 'w')
    # Reset the SPI interface for some reason..
    controller.reset_spi()
    # Set up some flashy lights
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(LED_RUNNING, GPIO.OUT)
    # Start GPS threadstoreAlienTelemetry
    GPS.start()
    # Start the Pilot
    PILOT.start()
    # Start the Telemetry handler
    TELEM.start()
    # Start ORIENT sensor thread
    ORIENT.start()
    # Start Camera thread
    CAMERA.start()
    

def shutDown():
    global data_dump_file
    LOG.info("Shutting down")
    data_dump_file.close()
    TELEM.stop()
    PILOT.stop()
    GPS.stop()
    ORIENT.stop()
    CAMERA.stop()


def alert(msg):
    text = str(msg)


def getOverrideState():
    LOG.info("Returning override state: %s" % OVERRIDE_STATE)
    return OVERRIDE_STATE


def setOverrideState(newstate):
    global OVERRIDE_STATE
    LOG.warning("Setting override state: %s" % newstate)
    OVERRIDE_STATE = newstate

def set_current_state(current_state):
    global CURRENT_STATE
    CURRENT_STATE = current_state
    TELEM.set_state(CURRENT_STATE)

def setPitchAngle(newAngle):
    try:
        angle = math.radians(float(newAngle))
        PILOT.updatePitch(angle)
    except Exception, e:
        LOG.error(e)


def setTurnSeverity(newSev):
    try:
        PILOT.updateTurnSev(newSev)
    except Exception, e:
        LOG.error(e)


def setDestination(lat, lon):
    PILOT.updateDestination(lat, lon)


def speak(text, speed=150):
    LOG.info("Speaking %s" % text)
    with open(os.devnull, "w") as devnull:
        subprocess.Popen(["espeak", "-k10 -s%s" % (speed), text], stdout=devnull, stderr=devnull)


def sendImage():
    newest_image = max(glob.iglob('%s/low_*.jpg' % CAMERA.photo_path), key=os.path.getctime)
    RADIO.sendImage(newest_image)


#################
# WING MOVEMENTS
#################
def center_wings():
    lcenter, rcenter, servoRange = PILOT.getWingCenterAndRange()
    setWingAngle([lcenter, rcenter])


def min_wings():
    lcenter, rcenter, servoRange = PILOT.getWingCenterAndRange()
    setWingAngle([lcenter - servoRange, rcenter - servoRange])


def max_wings():
    lcenter, rcenter, servoRange = PILOT.getWingCenterAndRange()
    setWingAngle([lcenter + servoRange, rcenter + servoRange])


def setWingAngle(angles):
    leftAngle = angles[0]
    rightAngle = angles[1]
    LOG.debug("Setting: %d %d" % (leftAngle, rightAngle))
    controller.W_glider_command("W:%2.2f:%2.2f" % (leftAngle, rightAngle))


def updateWingAngles():
    wingAngles = PILOT.get_servo_angles()
    LOG.debug("Wing angles received: %s" % wingAngles)
    if wingAngles:
        setWingAngle(wingAngles)


########################
# Release Chute/Balloon
########################
def releaseChord():
    CAMERA.take_video(15)
    controller.W_glider_command("D:")


def releaseParachute():
    CAMERA.take_video(15)
    controller.W_glider_command("P:")


########################
# Alien Telemetry
########################
def storeAlienTelemetry(telemetry_string, callsign):
    LOG.debug("Storing Alien Telemetry for %s: (%s)" % (callsign, telemetry_string))
    TELEM.alien_gps_dump[callsign] = telemetry_string