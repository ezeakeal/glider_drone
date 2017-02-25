##############################################
#
# GliderV2 Client Software 
# Author: Daniel Vagg
# 
##############################################
import os
import log
import time
import serial
import logging
import traceback
from xbee import XBee
from threading import Thread
from sat_radio import SatRadio

# GUIDE
# http://ava.upuaut.net/?p=768

##########################################
# GLOBALS
##########################################
LOG = log.setup_custom_logger('radio')
LOG.setLevel(logging.WARNING)

class GliderRadio(SatRadio):
    
    def __init__(self, port, callsign, baud_rate=38400, callback=None):
        self.ready = True
        SatRadio.__init__(self, port, callsign, baud_rate=baud_rate, callback=callback)

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


#---------- END CLASS -------------
