import log
import time
import logging
import datetime

import spidev

##########################################
# TODO
##########################################

##########################################
# GLOBALS
##########################################
delay_reset = 0.1
delay_xfer = 0.05
spi_bus = 0
spi_dev = 0
spi = None
wing_angle = 0
max_speed = 40000 # fuckit.. keep it that low.

LOG = log.setup_custom_logger('ATMEGA')
LOG.setLevel(logging.WARNING)

##########################################
# FUNCTIONS
##########################################
def W_glider_command(command):
    comm_string = "$%s;" % command
    LOG.debug("Sending %s" % comm_string)
    char_arr = [ord(i) for i in comm_string]
    
    while True:
        response = raw_xfer(char_arr)
        if response == char_arr:
            break
        else:
            reset_spi()
        time.sleep(delay_reset)


def raw_xfer(bytestr):
    send_arr = bytestr + [0] # add blank byte to receive the last character sent in response 
    LOG.debug("Transferring %s" % bytestr)
    response = spi.xfer(send_arr)
    response = response[1:] # remove first char as it contains a copy of the blank from last command
    LOG.debug("Response %s" % response)
    time.sleep(delay_xfer)
    LOG.debug("Response matched? %s" % (response == bytestr))
    return response


def hex_str(dec_str):
    return ''.join(["0x%02X " % x for x in dec_str]).strip()


def reset_spi():
    global spi
    LOG.debug("Restting SPI")
    if not spi:
        spi = spidev.SpiDev()
    spi.close()
    time.sleep(1)
    spi.open(spi_bus, spi_dev)
    spi.max_speed_hz = max_speed
