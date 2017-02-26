import logging

REDIS_IP="127.0.0.1"
REDIS_PORT=6379
REDIS_DB=0
LOGLEVEL=logging.DEBUG



def setup_custom_logger(name):
    formatter = logging.Formatter(fmt='%(asctime)s - %(levelname)s - %(module)s - %(message)s')

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    logger = logging.getLogger("glider.%s" % name)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)#
    logger.setLevel(LOGLEVEL)
    return logger
