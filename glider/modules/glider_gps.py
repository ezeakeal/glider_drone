import logging
from gps3.agps3threaded import AGPS3mechanism
# https://pypi.python.org/pypi/gps3/

LOG = logging.getLogger("glider.%s" % __name__)


class GPS(object):

    def __init__(self):
        # Instantiate AGPS3 Mechanisms
        self.gps3_thread = AGPS3mechanism()
        # From localhost (), or other hosts, by example, (host='gps.ddns.net')
        self.gps3_thread.stream_data()

    def start(self):
        LOG.info("Starting GPS thread now")
        # Throttle time to sleep after an empty lookup, default '()' 0.2 two tenths of a second
        self.gps3_thread.run_thread()

    def stop(self):
        LOG.info("Stopping GPS thread now")
        self.gps3_thread.stop()

    @property
    def data(self):
        return self.gps3_thread.data_stream
