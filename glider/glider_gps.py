import logging
from gps3.agps3threaded import AGPS3mechanism
# GUIDE
# http://ava.upuaut.net/?p=768
# https://pypi.python.org/pypi/gps3/

LOG = logging.getLogger('gps')

class GPS_USB(object):

    def __init__(self):
        self.gps3_thread = AGPS3mechanism()  # Instantiate AGPS3 Mechanisms
        self.gps3_thread.stream_data()  # From localhost (), or other hosts, by example, (host='gps.ddns.net')

    def start(self):
        LOG.info("Starting GPS thread now")
        self.gps3_thread.run_thread()  # Throttle time to sleep after an empty lookup, default '()' 0.2 two tenths of a second

    def stop(self):
        LOG.info("Stopping GPS thread now")
        self.gps3_thread.stop()

    @property
    def data(self):
        return self.gps3_thread.data_stream
