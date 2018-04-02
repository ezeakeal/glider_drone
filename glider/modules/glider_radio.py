##############################################
#
# GliderV3 Client Software
# Author: Daniel Vagg
# 
##############################################
import base64
import os
import logging
import traceback
from threading import Thread

import time

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

        self.push_data = False
        self.data_packet_queue = []

        port = glider_config.get("radio", "port")
        callsign = glider_config.get("radio", "callsign")
        baud_rate = glider_config.get("radio", "baud_rate")
        address = int(glider_config.get("radio", "address"), 16)
        super(self.__class__, self).__init__(port, address, callsign, baud_rate=baud_rate, callback=callback)

    def send_data(self, data):
        LOG.debug("Sending Data: %s to %s" % (data, self.groundstation_address))
        packet = "|".join(["D"] + data)
        self.send_packet(packet, address=self.groundstation_address)

    def start(self):
        super(self.__class__, self).start()
        self.push_data = True
        self.queue_push_thread = Thread(target=self._queued_push_data, args=[])
        self.queue_push_thread.start()

    def stop(self):
        self.push_data = False
        self.queue_push_thread.join()
        super(self.__class__, self).stop()

    def sendImage(self, image_path):
        LOG.warning("Sending Image: %s" % image_path)
        packet_bit_rate = 220
        # Start
        try:
            self.data_packet_queue.append("I|S|%s" % image_path)
            packet_index = 0
            image_size = os.path.getsize(image_path)
            total_packets = image_size/packet_bit_rate
            with open(image_path, "rb") as image:
                data = image.read()
                if not data:
                    return
            encoded_data = base64.b64encode(data)
            while encoded_data:
                self.data_packet_queue.append("I|P|%s|%s" % (packet_index, bytearray(encoded_data[:packet_bit_rate])))
                encoded_data = encoded_data[packet_bit_rate:]
                packet_index += 1
            # End
            self.data_packet_queue.append("I|E|%s" % image_path)
            LOG.warning("Set the packet_queue: %s" % self.data_packet_queue)
        except Exception:
            LOG.critical(traceback.format_exc())

    def _queued_push_data(self):
        while self.push_data:
            data_queue_length = len(self.data_packet_queue)
            if data_queue_length > 0:
                LOG.warning("Sending image part. Queue length: %s" % data_queue_length)
                data_part = self.data_packet_queue.pop(0)
                self.send_packet(data_part, address=self.groundstation_address)
            time.sleep(1)
#---------- END CLASS -------------
