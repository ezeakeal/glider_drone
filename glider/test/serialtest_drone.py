import time
from sat_radio import SatRadio

def cb(packet):
    print "Received packet: %s" % packet
    n = time.time()
    with open("/home/pi/packets_ground.dat", "a") as f:
        f.write("[%s] %s\n" % (n, packet))
    sr.send_packet("RSSI: %s" % packet.get("rssi"))

sr = SatRadio('/dev/ttyAMA0', 0xAA, "Drone", callback=cb)

def main():
    while True:
        try:
            time.sleep(5)
        except KeyboardInterrupt as e:
            print("Exiting")
            break
        except:
            print("Unexpected error")

main()
sr.stop()
