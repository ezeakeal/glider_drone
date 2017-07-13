import os
import time
import logging
import picamera

from PIL import Image
from datetime import datetime
from threading import Thread
from . import glider_config

LOG = logging.getLogger("Camera")
LOG.setLevel(logging.DEBUG)


class GliderCamera(object):
    threads = []

    def __init__(self, 
        low_quality_interval=15,
        high_quality_interval=60,
        photo_path=None):
        LOG.info("Camera init")
        if not photo_path:
            photo_path = glider_config.get("camera", "data_dir")
        self.photo_path = photo_path
        self.last_low_pic = time.time()
        self.last_high_pic = time.time()
        self.low_quality_interval = low_quality_interval
        self.high_quality_interval = high_quality_interval
        self.video_requested = 0


    def get_cam(self, cam_type):
        camera = picamera.PiCamera()
        camera.sharpness = 0
        camera.contrast = 0
        camera.brightness = 50
        camera.saturation = 0
        camera.image_effect = 'none'
        camera.color_effects = None
        camera.rotation = 0
        camera.hflip = True
        camera.vflip = False
        camera.video_stabilization = True
        camera.exposure_compensation = 0
        camera.exposure_mode = 'auto'
        camera.meter_mode = 'average'
        camera.awb_mode = 'auto'
        camera.crop = (0.0, 0.0, 1.0, 1.0)
        if cam_type == "high":
            camera.resolution = (1296, 972)
        if cam_type == "low":
            camera.resolution = (640, 480)
        if cam_type == "video":
            camera.resolution = (1296,972)             
        return camera 

    def _take_video(self):
        timestamp = datetime.now().strftime("%H%M%S%f")
        out_path = os.path.join(self.photo_path, "video_%s.h264" % timestamp)
        LOG.info("Creating (%ss) video at %s" % (self.video_requested, out_path))
        with self.get_cam("video") as camera:
            LOG.info("Starting recording")
            camera.start_recording(out_path)
            camera.wait_recording(self.video_requested)
            LOG.info("Stopping recording")
            camera.stop_recording()
            camera.close()
        return out_path

    def take_video(self, seconds):
        self.video_requested = seconds

    def take_low_pic(self):
        timestamp = datetime.now().strftime("%H%M%S%f")
        out_path = os.path.join(self.photo_path, "low_%s.jpg" % timestamp)
        with self.get_cam("low") as camera:
            camera.capture("/tmp/precompressed.jpg", format="jpeg", quality=40)
            image = Image.open("/tmp/precompressed.jpg")
            image.convert('P', palette=Image.ADAPTIVE, colors=200).convert("RGB").save(
                out_path, "JPEG", quality=20, optimize=True
            )
            camera.close()
        return out_path

    def take_high_pic(self):
        timestamp = datetime.now().strftime("%H%M%S%f")
        out_path = os.path.join(self.photo_path, "high_%s.png" % timestamp)
        with self.get_cam("high") as camera:
            camera.capture(out_path, format="png")
            camera.close()
        return out_path

    def take_pictures(self):
        while self.threadAlive:
            now = time.time() 
            if self.video_requested:
                out_path = self._take_video()
                self.video_requested = 0
                LOG.debug("Created video: %s" % out_path)
            if now - self.last_low_pic > self.low_quality_interval:
                out_path = self.take_low_pic()
                self.last_low_pic = now
                LOG.debug("Created low pic: %s" % out_path)
            if now - self.last_high_pic > self.high_quality_interval:
                out_path = self.take_high_pic()
                self.last_high_pic = now
                LOG.debug("Created high pic: %s" % out_path)
            time.sleep(1)

    def start(self):
        cameraThread = Thread( target=self.take_pictures, args=() )
        self.threadAlive = True
        LOG.info("Starting up Camera thread now")
        cameraThread.start()
        self.threads.append(cameraThread)

    def stop(self):
        self.threadAlive = False
        for t in self.threads:
            t.join()