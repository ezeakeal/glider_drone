# https://learn.sparkfun.com/tutorials/programming-the-pcduino/spi-communications

import spidev
import time

###########################
# Globals
###########################
delay_reset = 0.1
delay_xfer = 0.05
spi_bus = 0
spi_dev = 0
spi = None
wing_angle = 0

def W_glider_command(command):
    comm_string = "$%s;" % command
    char_arr = [ord(i) for i in comm_string]
    # print "Command = %s" % (comm_string)
    
    while True:
        response = raw_xfer(char_arr)
        if response == char_arr:
            # print "Success"
            break
        else:
            # print "Failure"
            reset_spi()
        time.sleep(delay_reset)


def raw_xfer(bytestr):
    send_arr = bytestr + [0] # add blank byte to receive the last character sent in response 
    print "Sending hex array: %s" % hex_str(send_arr)
    response = spi.xfer(send_arr)
    response = response[1:] # remove first char as it contains a copy of the blank from last command
    print "Received hex array: %s" % hex_str(response)
    time.sleep(delay_xfer)
    return response


def hex_str(dec_str):
    return ''.join(["0x%02X " % x for x in dec_str]).strip()


def doServoLoop():
    global wing_angle
    wing_angle += 2
    W_glider_command("W:%s:%s" % (wing_angle % 90, (wing_angle + 45) % 90))


def reset_spi():
    global spi
    if not spi:
        spi = spidev.SpiDev()
    spi.close()
    time.sleep(1)
    spi.open(spi_bus, spi_dev)
    spi.max_speed_hz = 40000 # fuckit.. keep it that low.


if __name__ == '__main__':
    reset_spi()
    while True:
        doServoLoop()
    spi.close()
        