import os
base_dir = os.path.dirname(__file__)
conf_path = os.path.join(base_dir, "glider_conf.ini")

# Configure the logger
from logging.config import fileConfig
fileConfig(conf_path)

