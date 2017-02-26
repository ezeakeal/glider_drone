import os
import log
import logging

from gps import *
from time import *
from threading import Thread
from glider.settings import *
# GUIDE
# http://ava.upuaut.net/?p=768

LOG = setup_custom_logger('gps')


class GPS_USB(object):

    def __init__(self):
        self.gpsd = gps(mode=WATCH_ENABLE) #starting the stream of info

    def poll_gps(self):
        while self.threadAlive:
            self.gpsd.next() #this will continue to loop and grab EACH set of gpsd info to clear the buffer
            LOG.debug("GPS data:")
            LOG.info('Error     %s %s' % (self.gpsd.fix.epx, self.gpsd.fix.epy))
            LOG.debug('latitude     %s' % self.gpsd.fix.latitude)
            LOG.debug('longitude    %s' % self.gpsd.fix.longitude)
            LOG.debug('time utc     %s + %s' % (self.gpsd.utc, self.gpsd.fix.time))
            LOG.debug('altitude (m) %s' % self.gpsd.fix.altitude)

    def start(self):
        pilotThread = Thread( target=self.poll_gps, args=() )
        self.threadAlive = True
        LOG.info("Starting up GPS thread now")
        pilotThread.start()

    def stop(self):
        self.threadAlive = False

    def getFix(self):
        return self.gpsd.fix

    def getLonLatDeg(self):
        lat = self.gpsd.fix.latitude
        lon = self.gpsd.fix.longitude
        return lon, lat

    def getTime(self):
        return self.gpsd.utc