#!/usr/bin/env python3
"""
Capture simulation sensor data and save as images.

Saves:
  /tmp/sim_color.png  — RGB camera
  /tmp/sim_depth.png  — Depth camera (normalized)
  /tmp/sim_lidar.png  — LiDAR top-down plot

Run: make dev.capture.sim
"""

import time
import math
import sys

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, LaserScan
import numpy as np


class SimCapture(Node):

    def __init__(self):
        super().__init__('sim_capture')
        self.color_saved = False
        self.depth_saved = False
        self.lidar_saved = False

        self.create_subscription(
            Image, '/robocept/camera/color/image_raw', self._color_cb, 10,
        )
        self.create_subscription(
            Image, '/robocept/camera/depth/image_rect_raw', self._depth_cb, 10,
        )
        self.create_subscription(
            LaserScan, '/robocept/lidar/scan', self._lidar_cb, 10,
        )
        self.get_logger().info('Waiting for sensor data...')

    @property
    def all_done(self):
        return self.color_saved and self.depth_saved and self.lidar_saved

    def _save_ppm(self, path, img_rgb):
        """Save RGB numpy array as PPM."""
        h, w = img_rgb.shape[:2]
        with open(path, 'wb') as f:
            f.write(f'P6\n{w} {h}\n255\n'.encode())
            f.write(img_rgb.tobytes())

    def _save_pgm(self, path, img_gray):
        """Save grayscale numpy array as PGM."""
        h, w = img_gray.shape[:2]
        with open(path, 'wb') as f:
            f.write(f'P5\n{w} {h}\n255\n'.encode())
            f.write(img_gray.tobytes())

    def _color_cb(self, msg):
        if self.color_saved:
            return
        self.color_saved = True
        w, h = msg.width, msg.height

        if msg.encoding == 'rgb8':
            img = np.frombuffer(msg.data, dtype=np.uint8).reshape(h, w, 3)
        elif msg.encoding == 'bgr8':
            img = np.frombuffer(msg.data, dtype=np.uint8).reshape(h, w, 3)
            img = img[:, :, ::-1]
        else:
            self.get_logger().warn(f'Unknown color encoding: {msg.encoding}')
            return

        self._save_ppm('/tmp/sim_color.ppm', img)

        # Also try PNG via PIL.
        try:
            from PIL import Image as PILImage
            PILImage.fromarray(img).save('/tmp/sim_color.png')
            self.get_logger().info(f'Saved /tmp/sim_color.png ({w}x{h})')
        except ImportError:
            self.get_logger().info(f'Saved /tmp/sim_color.ppm ({w}x{h})')

    def _depth_cb(self, msg):
        if self.depth_saved:
            return
        self.depth_saved = True
        w, h = msg.width, msg.height

        if '32FC1' in msg.encoding:
            depth = np.frombuffer(msg.data, dtype=np.float32).reshape(h, w)
        elif '16UC1' in msg.encoding:
            depth = np.frombuffer(msg.data, dtype=np.uint16).reshape(h, w)
            depth = depth.astype(np.float32) / 1000.0
        else:
            self.get_logger().warn(f'Unknown depth encoding: {msg.encoding}')
            return

        valid = depth[depth > 0]
        if len(valid) > 0:
            max_d = min(np.percentile(valid, 95), 10.0)
            norm = np.clip(depth / max_d * 255, 0, 255).astype(np.uint8)
        else:
            norm = np.zeros((h, w), dtype=np.uint8)

        self._save_pgm('/tmp/sim_depth.pgm', norm)

        try:
            from PIL import Image as PILImage
            PILImage.fromarray(norm).save('/tmp/sim_depth.png')
            self.get_logger().info(f'Saved /tmp/sim_depth.png ({w}x{h})')
        except ImportError:
            self.get_logger().info(f'Saved /tmp/sim_depth.pgm ({w}x{h})')

    def _lidar_cb(self, msg):
        if self.lidar_saved:
            return
        self.lidar_saved = True

        size = 500
        scale = size / 2 / 3.5
        img = np.zeros((size, size, 3), dtype=np.uint8)
        img[:] = 20

        # Range circles.
        for r in [1.0, 2.0, 3.0]:
            for a in range(720):
                x = int(size / 2 + r * scale * math.cos(math.radians(a / 2)))
                y = int(size / 2 - r * scale * math.sin(math.radians(a / 2)))
                if 0 <= x < size and 0 <= y < size:
                    img[y, x] = [40, 40, 40]

        # Robot.
        cx, cy = size // 2, size // 2
        for dx in range(-4, 5):
            for dy in range(-4, 5):
                if 0 <= cy + dy < size and 0 <= cx + dx < size:
                    img[cy + dy, cx + dx] = [0, 220, 0]

        # Scan points.
        n = 0
        for i, r in enumerate(msg.ranges):
            if r < msg.range_min or r > msg.range_max or r > 3.5:
                continue
            angle = msg.angle_min + i * msg.angle_increment
            x = int(size / 2 + r * scale * math.cos(angle))
            y = int(size / 2 - r * scale * math.sin(angle))
            for dx in range(-1, 2):
                for dy in range(-1, 2):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < size and 0 <= ny < size:
                        img[ny, nx] = [50, 130, 255]
            n += 1

        self.get_logger().info(f'LiDAR: {n} points plotted')
        self._save_ppm('/tmp/sim_lidar.ppm', img)

        try:
            from PIL import Image as PILImage
            PILImage.fromarray(img).save('/tmp/sim_lidar.png')
            self.get_logger().info('Saved /tmp/sim_lidar.png')
        except ImportError:
            self.get_logger().info('Saved /tmp/sim_lidar.ppm')


def main():
    rclpy.init()
    node = SimCapture()
    start = time.monotonic()
    while not node.all_done and time.monotonic() - start < 15:
        rclpy.spin_once(node, timeout_sec=0.5)

    if not node.color_saved:
        node.get_logger().warn('No color image received')
    if not node.depth_saved:
        node.get_logger().warn('No depth image received')
    if not node.lidar_saved:
        node.get_logger().warn('No LiDAR scan received')

    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
