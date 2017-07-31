import time
import struct
import logging
import crcmod.predefined

from threading import Thread

import serial

LOG = logging.getLogger('glider.rhserial')


crc16 = crcmod.predefined.mkCrcFun('crc-16-mcrf4xx')
DLE = 0x10
STX = 0x02
ETX = 0x03
BROADCAST = 0xFF

class RHSerial(object):

    def __init__(self, port, baud_rate=38400, address=0xFF, callback=None, promiscuous=False):
        self.serial = serial.Serial(port, baud_rate, bytesize=8, stopbits=1, parity=serial.PARITY_NONE, timeout=2)
        self.address = address
        self.callback = callback
        self.promiscuous = promiscuous
        self.listen = False
        self.listen_thread = None

    def start(self):
        if self.listen:
            raise Exception("RHserial is being started again. Don't do this! It screws the serial connection.")
        self.listen = True
        self.listen_thread = Thread(target=self._listen_for_msg, args=[])
        self.listen_thread.start()

    def stop(self):
        self.listen = False
        self.listen_thread.join()
        self.serial.close()

    def _listen_for_msg(self):
        message = bytearray()
        checksum = bytearray()
        state = 'IDLE'

        while self.listen:
            try:
                byte = self.serial.read()
                if byte:
                    if state == 'IDLE':
                        # looking for a DLE to start.
                        if ord(byte) == DLE:
                            # Got a DLE, enter STX state.
                            state = 'STX'
                    elif state == 'STX':
                        # looking for a STX to begin reading message.
                        if ord(byte) == STX:
                            # Got a STX, enter MESSAGE state and clear out message.
                            state = 'MESSAGE'
                            message = bytearray()
                    elif state == 'MESSAGE':
                        # looking for DLEs to either escpae a DLE or end the message.
                        if ord(byte) == DLE:
                            # Got a DLE, enter MSGDLE state.
                            state = 'MSGDLE'
                        else:
                            # It's part of the message, add it to the message.
                            message.append(ord(byte))
                    elif state == 'MSGDLE':
                        # Looking for a DLE or a ETX.
                        if ord(byte) == DLE:
                            # It's a DLE that's part of the message.
                            message.append(ord(byte))
                            state = 'MESSAGE'
                        elif ord(byte) == ETX:
                            # It's an ETX, we're done with the message, move on to the checksum.
                            message.append(DLE)
                            message.append(ETX)
                            state = 'CHECKSUM1'
                            checksum = bytearray()
                        else:
                            # This shouldn't have happened. Let's abort and go back to the IDLE state.
                            state = 'IDLE'
                    elif state == 'CHECKSUM1':
                        checksum.append(ord(byte))
                        state = 'CHECKSUM2'
                    elif state == 'CHECKSUM2':
                        checksum.append(ord(byte))
                        # All done, let's check the sum and process the message.
                        calcedcheck = bytearray(struct.pack(">H", crc16(str(message))))
                        if calcedcheck == checksum:
                            # Process message.
                            msgdict = self._processmsg(message)
                            if msgdict and self.callback:
                                self.callback(msgdict)
                        # Either we processed the message or it didn't pass the checksum, either way let's start over.
                        state = 'IDLE'
            except Exception as e:
                print "Throwing away unexpected exception (%s), resetting state"  % e
                time.sleep(1)
                state = 'IDLE'


    def send(self, msg, to=0xFF, id=0):
        if not self.serial.isOpen():
            raise Exception("Serial port is not open. Start thread to open port.")
        msghead = bytearray.fromhex("10 02")
        msgto = chr(to)
        msgfrom = chr(self.address)
        msgid = chr(id)
        msgflag = chr(0x00)
        message = bytearray(msg)
        msgtail = bytearray.fromhex("10 03")
        crc16 = crcmod.predefined.mkCrcFun('crc-16-mcrf4xx')
        checkable = msgto + msgfrom + msgid + msgflag + message + msgtail
        checksum = bytearray(struct.pack(">H", crc16(str(checkable))))
        full = msghead + checkable + checksum
        self.serial.write(full)

    def _processmsg(self, msg):
        msgto = msg[0]
        LOG.debug("raw: %s" % msg)
        if msgto in [BROADCAST, self.address] or self.promiscuous:
            msgfrom = msg[1]
            msgid = msg[2]
            rawrssi = msg[3]
            if rawrssi > 127:
                msgrssi = rawrssi - 256
            else:
                msgrssi = rawrssi
            payload = msg[4:-2]
            msgdict = {'to': msgto,
                        'from': msgfrom,
                        'id': msgid,
                        'rssi': msgrssi,
                        'message': payload,
                        }
            return msgdict
        else: return None