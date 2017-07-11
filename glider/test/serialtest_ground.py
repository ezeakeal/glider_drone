import sys
import time
from sat_radio import SatRadio

sys.path.append("/usr/lib/python2.7/dist-packages/")
from gps import *

class GPS_USB(object):
    def __init__(self):
        self.gpsd = gps(mode=WATCH_ENABLE) #starting the stream of info

    def poll_gps(self):
        while self.threadAlive:
            self.gpsd.next() #this will continue to loop and grab EACH set of gpsd info to clear the buffer

    def start(self):
        gpsthread = Thread( target=self.poll_gps, args=() )
        self.threadAlive = True
        gpsthread.start()

    def stop(self):
        self.threadAlive = False

    def getFix(self):
        return self.gpsd.fix

    def getTime(self):
        return self.gpsd.utc


def cb(packet):
    print "Received packet"
    n = time.time()
    with open("/home/dvagg/packets_ground.dat", "a") as f:
        f.write("%s,%s" % (n, packet))
    print(packet)

sr = SatRadio('/dev/ttyUSB0', 0xAA, "Ground", callback=cb)

def main():
    print("Starting")
    _gps = GPS_USB()
    while True:
        try:
            time.sleep(5)
            print("Sending")
            fix = _gps.getFix()
            sr.send_data("Time(%s) Alt(%s) Lat(%s) Lon(%s)" % (fix.time, fix.altitude, fix.latitude, fix.longitude))
        except KeyboardInterrupt:
            print "Exiting"
            break


main()
sr.stop()