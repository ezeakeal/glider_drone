import logging
from rhserial import RHSerial

LOG = logging.getLogger("glider.%s" % __name__)

class SatRadio(RHSerial):
    BROADCAST = 0xFF

    def __init__(self, port, address, callsign, baud_rate=38400, callback=None):
        self.frame_count = 1
        self.telem_index = 1
        self.callsign = callsign
        self.user_callback = callback
        self.radio = RHSerial(port, address=address, baud_rate=baud_rate, callback=self._callback)

    def _rx_callback(self, packet):
        # Could do something here, I dunno.
        pass


    def _callback(self, data):
        try:
            self._rx_callback(data)
            if self.user_callback:
                self.user_callback(data)
        except Exception, e:
            LOG.exception("Exception in data callback")

    def _construct_telemetry(self,
        callsign, index, hhmmss,
        lat_dec_deg, lon_dec_deg,
        lat_dil, alt,
        dest_lat_deg, dest_lon_deg,
        state):

        telem_str = "T|%s|%05d" % (callsign, index)
        # Time
        telem_str += hhmmss.strftime("|%H%M%S") if hhmmss else "|      "
        # GPS stuff
        telem_str += "|%+08.05f" % lat_dec_deg if type(lat_dec_deg) != str else "|        "
        telem_str += "|%+09.05f" % lon_dec_deg if type(lon_dec_deg) != str else "|         "
        telem_str += "|%05.02f" % lat_dil if type(lat_dil) != str else "|     "
        telem_str += "|%08.02f" % alt if type(alt) != str else "|        "

        telem_str += "|%+09.05f" % dest_lat_deg if type(dest_lat_deg) != str else "|         "
        telem_str += "|%+08.05f" % dest_lon_deg if type(dest_lon_deg) != str else "|        "
        telem_str += "|%s" % state

        return telem_str
 
    def _encode_data(self, data):
        return b'%s' % data
 
    def start(self):
        self.radio.start()
 
    def stop(self):
        self.radio.stop()
 
    def send_packet(self, data, address=0xFF):
        LOG.debug("Sending: %s" % data)
        frame_id = self.frame_count# struct.pack("B", self.frame_count)
        # Then try and transmit the packet
        self.radio.send(self._encode_data(data), to = address, id = frame_id)
        self.frame_count = ((self.frame_count + 1) % 250)

        return frame_id
 
    def send_telem(self, hhmmss, 
        lat_dec_deg, lon_dec_deg,
        lat_dil, alt,
        dest_lat_deg, dest_lon_deg,
        state):
        data = self._construct_telemetry(
            self.callsign.ljust(8)[:8], 
            self.telem_index, hhmmss, 
            lat_dec_deg, lon_dec_deg,
            lat_dil, alt,
            dest_lat_deg, dest_lon_deg,
            state
        )
        self.telem_index += 1
        return self.send_packet(data)
 
    def send_data(self, data):
        return self.send_packet(data)
