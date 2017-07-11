# glider_drone

A project to send a drone/glider to the stratosphere, and get it back!

## Recomendations

Setup remote debug (https://nathanpjones.com/2016/02/remote-debug-gpio-on-raspberry-pi/)

# Required hardware

1. Balloon (Hwoyee HY-1000) http://randomaerospace.com/Random_Aerospace/Balloons.html
2. Parachute (18 in. Spherachute + 42 in. Spherachute) http://spherachutes.com/
3. Glider (Go Discover FPV EPO) https://hobbyking.com/en_us/hobbykingr-tm-go-discover-fpv-plane-epo-1600mm-kit.html
4. Foil tape - reflectors
5. Copper tape - make dipole antenna out of glider structural rod
6. 2 LoRa radios
7. Raspberry Pi B 2
8. Raspberry Pi servo hat + sensor hats
9. LiIon battery packs (10000 mAh recommended.. I have 2)
10. GoPro or equivalent
11. Wide angle Raspberry Pi Camera (reverse view)

# Prerequisites

## Setup I2C

https://learn.adafruit.com/adafruits-raspberry-pi-lesson-4-gpio-setup/configuring-i2c

## Setup Raspberry Pi interfaces

Using `raspi-config` (https://learn.sparkfun.com/tutorials/raspberry-pi-spi-and-i2c-tutorial):
1. Enable I2C
2. Enable Camera
3. Enable Remote GPIO (optional - enabling now just in case I use it later)

test

# Internal notes

## Features:
    Homesickness routine:
        If no signal from groundstation received, do not disengage from balloon
        Probably send a flag (trust of glider behaviour = True/False)
            So during flight, you flick that switch in groundstation
    Dual antennas:
        Two orientations during flight (vertical, and gliding)
        So two antennas
    IMU mounted away from electronics
    LEDs for status:
        Help Debug whats going on (issue was disk mounting this time)
    Shielded servo lines
    SMS also
    Directional tracker
    Return to sender information (like who the fuck I am)
    Better FSTAB control - must mount everytime!

## Nice to have:
    Smoke trails
    Fireworks
    Loud beeper for finding
    Groundstation application which shows where the satellites are with overlay on camera!

## Todo list:
    Fix the GPS tracking in the IMU module
        GPS tracking set the offset for the IMU, but tracking was degrees, IMU was radians

## Flight tests:
    Shake test
    Radar test (ticknock to elsewhere)
    Parachute test

newline