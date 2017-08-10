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
6. 2 LoRa radios (http://www.hoperf.com/rf_transceiver/lora/RFM95W.html) with some interface.
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

## Setup the disks

The glider will record video and logs to a directory specified in `glider_conf.ini`
For example, images/videos will be written to `/data/camera' by default.
Make any required directories before execution (I recommend using a USB stick)

## Calibrate the MPU

https://github.com/RTIMULib/RTIMULib2/blob/master/Calibration.pdf

Follow all the instructions for callibration (run RTIMULibCal inside of RTEllipsoidFit)
This will generate an RTIMULib.ini config file - move that to a well-known path.
Finally, set the full path to the RTIMULib.ini file in glider_conf.ini

## Setup the Servo Hat

Oh heavens. I will never buy from banggood again.
* The sensor board I got breaks the MPU - wont initialize.
    * https://www.banggood.com/4-in-1-Temperature-Pressure-Altitude-Light-Sensor-Module-p-965547.html
* The servo hat had no documentation online, but I eventually found it from a comment:
    * From a comment here: http://club.dx.com/forums/Forums.dx/threadid.1440743
    * http://m5.img.dxcdn.com/CDDriver/xrj/340853.zip
    * Then open the docx with the crazy characters.
    * Here is the git repo they use: https://github.com/geekroo/Geekroo-PiCobber-PWMServo.git
    * It's HEAVILY inspired by https://learn.adafruit.com/adafruit-16-channel-pwm-servo-hat-for-raspberry-pi/library-reference

## Find the range of your servos

The min/max duty cycle of the servo pulse can be configured in the settings.

**Note:** It took me some trial and error to figure this out (read Weird things below)

Using the PWM controller library from Adafruit or geekroo, start sending pulses to your servo.
I did the following

```
from Adafruit_PWM_Servo_Driver import PWM
import time
pwm = PWM(0x70) # i2c address for the servo hat controller
pwm.setPWMFreq(50)

# Try find min/max angle values
# pwm.setPWM(0,0, int(4096/20*(pulse_fraction)))
# I decreased the value of pulse_fraction from 1, to 0.7 until the servo stopped moving
# Then I increased the value until it stopped moving the other way
# The command is setting the pulse duration (in multiples of 1ms out of 20ms pulse)
# So pulse_fraction = 1 means 1ms@5V, then 19ms@0V

# The min I found
pwm.setPWM(0,0, int(4096/20*(0.7)))
# The max I found
pwm.setPWM(0,0, int(4096/20*(2.6)))
```

Once you have these values, set them in glider_conf.ini

### Weird things that happened

When I was trying to test the servos, some weird things happened before I found the range.

* Servo was sweeping through 30 or 40 degrees when I tried setting a new pulse width.
    * Not like a jitter or twitch, this was random sweeping for a few fractions of a second each time.
    * I thought that the servo was broken or frequency was wrong.
    * They were bad assumptions. Turns out that doubling the frequency reduced the symptom
        * Initial pulse was now reasonable in some cases!
        * But a second pulse was being sent, causing weirdness.
* Generally: if a pulse is 20ms long (50hz frequency), then:
    * 2ms high (5V) + 18ms low represents 180deg
    * 1ms high represents 0deg
* I was setting some mad values outside of this range
    * The library takes a the pulse width as a portion of 4096 (e.g. 1024 is 25% pulse width)
* **Important:** IF you give the servo a terrible value, it may not recover from trying to reach that, and future values may not work.
    * This is what led to such confusion on my part. I was putting the servo into a weird state because I lacked prior knowledge on servo pulses.


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

<iframe src="https://giphy.com/embed/S3Ot3hZ5bcy8o" width="480" height="375" frameBorder="0" class="giphy-embed" allowFullScreen></iframe><p><a href="https://giphy.com/gifs/jack-nicholson-nodding-anger-management-S3Ot3hZ5bcy8o">via GIPHY</a></p>

## Todo list:
    Fix the GPS tracking in the IMU module
        GPS tracking set the offset for the IMU, but tracking was degrees, IMU was radians

## Flight tests:
    Shake test
    Radar test (ticknock to elsewhere)
    Parachute test

newline