##############################################
#
# GliderV2 Client Software 
# Author: Daniel Vagg
# 
##############################################
import os
import logging
import traceback
from . import glider_config

##########################################
# GLOBALS
##########################################
LOG = logging.getLogger('radio')

class GliderRadio():
    
    def __init__(self, callback):
        self.ready = True
        port = glider_config.get("radio", "port")
        callsign = glider_config.get("radio", "callsign")
        baud_rate = glider_config.get("radio", "baud_rate")

    def send_data(self, data):
        address = self.ADDR_GLIDER_GROUNDSTATION
        LOG.debug("Sending Data: %s to %s" % (data, address))
        packet = "|".join(["D"] + data)
        self.send_packet(packet, address=address)

    def sendImage(self, image_path):
        LOG.warning("Sending Image: %s" % image_path)
        address = self.ADDR_GLIDER_GROUNDSTATION
        packet_bit_rate = 220
        # Start
        try:
            self.send_packet("I|S|%s" % image_path, address=address, mode=self.MODE_P2P)
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
                    self.send_packet(packet, address=address, mode=self.MODE_P2P)
                    packet_index += 1
            # End
            self.send_packet("I|E|%s" % image_path, address=address, mode=self.MODE_P2P)
        except Exception:
            LOG.critical(traceback.format_exc())

    def start(self):
        pass

    def stop(self):
        pass

#---------- END CLASS -------------
