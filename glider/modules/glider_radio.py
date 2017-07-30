##############################################
#
# GliderV2 Client Software 
# Author: Daniel Vagg
# 
##############################################
import os
import logging
import traceback
from sat_radio import SatRadio
from . import glider_config

##########################################
# GLOBALS
##########################################
LOG = logging.getLogger("glider.%s" % __name__)

class GliderRadio(SatRadio):
    
    def __init__(self, callback):
        self.ready = True
        self.groundstation_address = int(glider_config.get("radio", "groundstation_address"), 16)
        port = glider_config.get("radio", "port")
        callsign = glider_config.get("radio", "callsign")
        baud_rate = glider_config.get("radio", "baud_rate")
        address = int(glider_config.get("radio", "address"), 16)
        SatRadio.__init__(self, port, address, callsign, baud_rate=baud_rate, callback=callback)

    def send_data(self, data):
        LOG.debug("Sending Data: %s to %s" % (data, self.groundstation_address))
        packet = "|".join(["D"] + data)
        self.send_packet(packet, address=self.groundstation_address)

    def sendImage(self, image_path):
        LOG.warning("Sending Image: %s" % image_path)
        packet_bit_rate = 220
        # Start
        try:
            self.send_packet("I|S|%s" % image_path, address=self.groundstation_address)
            packet_index = 0
            image_size = os.path.getsize(image_path)
            total_packets = image_size/packet_bit_rate
            with open(image_path, "rb") as image:
                while True:
                    data = image.read(packet_bit_rate)
                    if not data:
                        break
                    # Part
                    packet = "I|P|%s|%s" % (packet_index, bytearray(data))
                    LOG.warning("Sending image part: %s of %s" % (packet_index, total_packets))
                    self.send_packet(packet, address=self.groundstation_address)
                    packet_index += 1
            # End
            self.send_packet("I|E|%s" % image_path, address=self.groundstation_address)
        except Exception:
            LOG.critical(traceback.format_exc())

#---------- END CLASS -------------
