import os
import time
from unittest import TestCase
from glider.modules.glider_camera import GliderCamera

class TestGliderCamera(TestCase):
    MAX_LOWRES_PIC_SIZE_BYTES = 50 * 10**3 # 50kb max
    MIN_HIGHRES_PIC_SIZE_BYTES = 50 * 10 ** 4  # 500kb max

    def setUp(self):
        self.camera = GliderCamera()
        self.camera.start()
        self.data_dir = self.camera.photo_path

    def tearDown(self):
        self.camera.stop()
        time.sleep(2)

    def test_get_cam(self):
        cam = self.camera.get_cam("low")
        self.assertEqual(cam.resolution, (640, 480))
        cam.close()

    def test_take_video(self):
        data_content = os.listdir(self.camera.photo_path)
        self.camera.take_video(3)
        time.sleep(5) # wait for the camera thread to take the video
        new_data_content = os.listdir(self.camera.photo_path)
        added_content = set(new_data_content) - set(data_content)
        self.assertEqual(len(added_content), 1)

    def test_take_low_pic(self):
        data_content = os.listdir(self.camera.photo_path)
        self.camera.take_low_pic()
        time.sleep(3)  # wait for the camera thread to take the video
        new_data_content = os.listdir(self.camera.photo_path)
        added_content = set(new_data_content) - set(data_content)
        assert (len(added_content) == 1)
        low_cam_file = os.path.join(self.camera.photo_path, list(added_content)[0])
        file_size = os.stat(low_cam_file).st_size
        self.assertLess(file_size, self.MAX_LOWRES_PIC_SIZE_BYTES)

    def test_take_high_pic(self):
        data_content = os.listdir(self.camera.photo_path)
        self.camera.take_high_pic()
        time.sleep(3)  # wait for the camera thread to take the video
        new_data_content = os.listdir(self.camera.photo_path)
        added_content = set(new_data_content) - set(data_content)
        assert (len(added_content) == 1)
        low_cam_file = os.path.join(self.camera.photo_path, list(added_content)[0])
        file_size = os.stat(low_cam_file).st_size
        self.assertGreater(file_size, self.MIN_HIGHRES_PIC_SIZE_BYTES)

