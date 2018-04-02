# Get the config
import os
import ConfigParser

base_dir = os.path.dirname(__file__)
conf_path = os.path.join(base_dir, "glider_conf.ini")

glider_config= ConfigParser.ConfigParser()
glider_config.read(conf_path)