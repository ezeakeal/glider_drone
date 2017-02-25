import time
import serial
import struct
 
from xbee import ZigBee
 
 
class SatRadio(object):
    DEFAULT_SHORT_ADDR = 'FFFE'
    MODE_P2P="POINT_TO_POINT"
    MODE_P2MP="POINT_TO_MULTIPOINT"

    ADDR_GLIDER = "0013A200408BDF64"
    ADDR_GLIDER_GROUNDSTATION = "0013A20040A38FD1"
 
    def __init__(self, port, callsign, baud_rate=38400, callback=None):
        self.port = port
        self.baud_rate = baud_rate
        self.serial_port = None
        self.xbee = None
        self.frame_count = 1
        self.telem_index = 1
        self.callsign = callsign
        self.radio_buffer = {}
        self.user_callback = callback
        self.start()
 
    def _rx_callback(self, packet):
        packet_id = packet['id']
        if packet_id != 'tx_status':
            # print "NON_TX CALLBACK"
            pass
 
    def _tx_callback(self, packet):
        packet_id = packet['id']
        if packet_id == 'tx_status':
            frame_id = packet['frame_id']
            if frame_id in self.radio_buffer.keys():
                self.radio_buffer.pop(frame_id)
 
    def _callback(self, data):
        try:
            self._rx_callback(data)
            self._tx_callback(data)
            if self.user_callback:
                self.user_callback(data)
        except Exception, e:
            print "Exception in data _callback: %s" % e
 
    def _construct_telemetry(self, 
        callsign, index, hhmmss, 
        lat_dec_deg, lon_dec_deg,
        lat_dil, alt,
        temp1, temp2,
        pressure):
        telem_str = "T|%s" % (callsign)
        telem_str += "|%05d|%06d" % (index, hhmmss)
        telem_str += "|%c|%02.05f|%c|%02.05f|%02.02f|%05.2f" % (
             "N" if lat_dec_deg > 0 else "S", abs(lat_dec_deg), 
             "E" if lon_dec_deg > 0 else "W", abs(lon_dec_deg), 
            lat_dil, alt, 
        )
        telem_str += "|%c%03.03f|%c%03.03f" % (
            "+" if temp1 > 0 else "-", abs(temp1),
            "+" if temp2 > 0 else "-", abs(temp2)
        )
        telem_str += "|%04.04f" % (pressure)
        return telem_str
 
    def _encode_data(self, data):
        return b'%s' % data
 
    def _transmit_complete(self, max_radio_buffer_size=1, expire_seconds=3):
        now = time.time()
        new_buffer = {}
        for key, value in self.radio_buffer.items():
            if now - value < expire_seconds:
                new_buffer[key] = value
            else:
                print "Dropped frame (%s)" % key
        self.radio_buffer = new_buffer
        return len(self.radio_buffer) < max_radio_buffer_size
 
    def start(self):
        self.serial_port = serial.Serial(self.port, self.baud_rate)
        self.xbee = ZigBee(self.serial_port, callback=self._callback)
 
    def stop(self):
        self.xbee.halt()
        self.serial_port.close()
 
    def send_packet(self, data, 
            default_short=None,
            address=None,
            mode=MODE_P2P, 
            sleep_time=0.05):
        # Get hex addresses
        short_hex_addr = (default_short or self.DEFAULT_SHORT_ADDR).decode("hex")
        if mode == self.MODE_P2MP:
            long_hex_addr = "000000000000FFFF".decode("hex")
        elif address:
            long_hex_addr = address.decode("hex")
        else:
            raise Exception("Address must be specified if not using MODE_P2MP")
        # Determine the frame_id and append it to a radio buffer so we dont send too much data too fast
        frame_id = struct.pack("B", self.frame_count)
        self.radio_buffer[frame_id] = time.time()
        # Then try and transmit the packet
        self.xbee.tx(
            dest_addr=short_hex_addr, 
            dest_addr_long=long_hex_addr, 
            data=self._encode_data(data), 
            frame_id=frame_id
        )
        self.frame_count = ((self.frame_count + 1) % 250)
        # Are we ready to move on
        while not self._transmit_complete():
            time.sleep(sleep_time)
        return frame_id
 
    def send_telem(self, hhmmss, 
        lat_dec_deg, lon_dec_deg,
        lat_dil, alt,
        temp1, temp2,
        pressure):
        data = self._construct_telemetry(
            self.callsign.ljust(8, ' '), 
            self.telem_index, hhmmss, 
            lat_dec_deg, lon_dec_deg,
            lat_dil, alt,
            temp1, temp2,
            pressure
        )
        self.telem_index += 1
        return self.send_packet(data, mode=self.MODE_P2MP)
 
    def send_data(self, data):
        return self.send_packet(data, mode=self.MODE_P2MP)