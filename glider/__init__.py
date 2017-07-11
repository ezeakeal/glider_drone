import os
base_dir = os.path.dirname(__file__)

# Get the config
import ConfigParser
Config = ConfigParser.ConfigParser()
glider_config = Config.read(os.path.join(base_dir, "glider_conf.ini"))

# Configure the logger
from logging.config import fileConfig
fileConfig(os.path.join(base_dir, 'logging.ini'))

