from unittest import TestCase
from glider.modules.glider_imu import IMU
import time

class TestIMU(TestCase):
    def setUp(self):
        self.imu_reader = IMU()

    def tearDown(self):
        pass

    def test_orientationValued(self):
        old_yaw = self.imu_reader.yaw
        old_roll = self.imu_reader.roll
        old_pitch= self.imu_reader.pitch
        self.assertIsNotNone(old_yaw)
        self.assertIsNotNone(old_pitch)
        self.assertIsNotNone(old_roll)

    def test_orientationChange(self):
        old_yaw = self.imu_reader.yaw
        time.sleep(1)
        new_yaw = self.imu_reader.yaw
        self.assertNotEqual(old_yaw, new_yaw)

