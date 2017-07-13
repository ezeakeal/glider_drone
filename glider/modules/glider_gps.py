import json
import logging
import os

from gps3.agps3threaded import AGPS3mechanism
from . import glider_config
# https://pypi.python.org/pypi/gps3/

LOG = logging.getLogger("glider.%s" % __name__)


class GPS(object):

    def __init__(self):
        # Instantiate AGPS3 Mechanisms
        self.gps3_thread = AGPS3mechanism()
        # From localhost (), or other hosts, by example, (host='gps.ddns.net')
        self.gps3_thread.stream_data()
        # Used for debugging purposes
        fake_location = glider_config.get("gps", "fake_location")
        if fake_location and os.path.exists(fake_location):
            LOG.warning("Using fake data file! %s" % fake_location)
            self.fake_location_file = fake_location

    def start(self):
        LOG.info("Starting GPS thread now")
        # Throttle time to sleep after an empty lookup, default '()' 0.2 two tenths of a second
        self.gps3_thread.run_thread()

    def stop(self):
        LOG.info("Stopping GPS thread now")
        self.gps3_thread.stop()

    @property
    def data(self):
        data = self.gps3_thread.data_stream
        if self.fake_location_file:
            with open(self.fake_location_file) as fake_file:
                fake_data = json.load(fake_file)
                for key, val in fake_data.items():
                    setattr(data, key, val)
        return data
