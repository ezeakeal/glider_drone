
LOG = logging.getLogger('operations')

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
GPS = GPS_USB()
ORIENT = IMU() # yaw should be 0 when north
CAMERA = GliderCamera()
RADIO = GliderRadio("/dev/ttyAMA0", "GliderV3", callback=dataHandler)
PILOT = Pilot(ORIENT, GPS, desired_pitch=-math.radians(30))
TELEM = TelemetryHandler(RADIO, ORIENT, PILOT, GPS)

##########################################
# GLOBALS
##########################################
OVERRIDE_STATE = None
CURRENT_STATE = None

# --- LED ---
LED_RUNNING = 11

##########################################
# FUNCTIONS - START/STOP
##########################################



#####################################################################
# FUNCTIONS - Awkward methods of sharing information on glider state
#####################################################################
