#!/usr/bin/env python3
"""
Automated obstacle avoidance test in simulation.

Prerequisites:
  1. Simulation running:  make dev.run.sim
  2. Obstacle avoider:    make dev.run.obstacle

This test:
  1. Resets robot to center of the room
  2. Sends forward velocity toward the north wall
  3. Monitors /cmd_vel — verifies obstacle avoider reduces speed and stops
  4. Sends velocity toward an obstacle
  5. Verifies emergency stop and rotation away

Run: make dev.test.obstacle
  or: python3 test_obstacle_avoidance_sim.py
"""

import sys
import time
import math

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from sensor_msgs.msg import LaserScan


class ObstacleAvoidanceTest(Node):

    def __init__(self):
        super().__init__('obstacle_avoidance_test')

        self.cmd_vel_received = []
        self.latest_odom = None
        self.latest_scan = None
        self.pass_count = 0
        self.fail_count = 0

        # Publishers.
        self.nav_pub = self.create_publisher(Twist, '/nav_cmd_vel', 10)

        # Subscribers.
        self.cmd_sub = self.create_subscription(
            Twist, '/cmd_vel', self._cmd_vel_cb, 10,
        )
        self.odom_sub = self.create_subscription(
            Odometry, '/odom', self._odom_cb, 10,
        )
        self.scan_sub = self.create_subscription(
            LaserScan, '/robocept/lidar/scan', self._scan_cb, 10,
        )

    def _cmd_vel_cb(self, msg):
        self.cmd_vel_received.append({
            'time': time.monotonic(),
            'linear_x': msg.linear.x,
            'angular_z': msg.angular.z,
        })

    def _odom_cb(self, msg):
        self.latest_odom = msg

    def _scan_cb(self, msg):
        self.latest_scan = msg

    def send_nav_cmd(self, linear_x, angular_z, duration_sec):
        """Send a velocity command for a duration."""
        cmd = Twist()
        cmd.linear.x = linear_x
        cmd.angular.z = angular_z

        start = time.monotonic()
        rate = self.create_rate(20)
        while time.monotonic() - start < duration_sec:
            self.nav_pub.publish(cmd)
            rclpy.spin_once(self, timeout_sec=0.01)
            rate.sleep()

    def stop(self):
        """Send zero velocity."""
        cmd = Twist()
        for _ in range(10):
            self.nav_pub.publish(cmd)
            rclpy.spin_once(self, timeout_sec=0.01)
            time.sleep(0.05)

    def wait_for_data(self, timeout=5.0):
        """Wait until we have odom and scan data."""
        start = time.monotonic()
        while time.monotonic() - start < timeout:
            rclpy.spin_once(self, timeout_sec=0.1)
            if self.latest_odom is not None and self.latest_scan is not None:
                return True
        return False

    def get_front_min_distance(self):
        """Get minimum distance in front 60-degree arc from latest scan."""
        if self.latest_scan is None:
            return float('inf')

        scan = self.latest_scan
        half_fov = math.radians(30)
        min_dist = float('inf')

        for i, r in enumerate(scan.ranges):
            if r < scan.range_min or r > scan.range_max:
                continue
            angle = scan.angle_min + i * scan.angle_increment
            angle = math.atan2(math.sin(angle), math.cos(angle))
            if abs(angle) <= half_fov and r < min_dist:
                min_dist = r

        return min_dist

    def check(self, name, condition, detail=""):
        """Assert a test condition."""
        if condition:
            self.pass_count += 1
            self.get_logger().info(f'  PASS: {name}')
        else:
            self.fail_count += 1
            self.get_logger().error(f'  FAIL: {name} — {detail}')

    def run_tests(self):
        self.get_logger().info('=' * 60)
        self.get_logger().info('Obstacle Avoidance Simulation Test')
        self.get_logger().info('=' * 60)

        # Wait for data.
        self.get_logger().info('\nWaiting for sensor data...')
        if not self.wait_for_data():
            self.get_logger().error('No data received. Is sim + obstacle_avoider running?')
            self.get_logger().error('  Terminal 1: make dev.run.sim')
            self.get_logger().error('  Terminal 2: make dev.run.obstacle')
            return False

        front_dist = self.get_front_min_distance()
        self.get_logger().info(f'Initial front distance: {front_dist:.2f}m')

        # ---- Test 1: Passthrough in open space ----
        self.get_logger().info('\n--- Test 1: Passthrough in open space ---')
        self.get_logger().info('Sending 0.3 m/s forward for 2 seconds...')
        self.cmd_vel_received.clear()
        self.send_nav_cmd(0.3, 0.0, 2.0)

        if self.cmd_vel_received:
            max_vel = max(c['linear_x'] for c in self.cmd_vel_received)
            self.check(
                'Forward velocity passed through',
                max_vel > 0.1,
                f'max cmd_vel.linear.x = {max_vel:.3f}',
            )
        else:
            self.check('Received cmd_vel messages', False, 'no cmd_vel received')

        self.stop()
        time.sleep(1.0)

        # ---- Test 2: Drive toward wall, verify slowdown ----
        self.get_logger().info('\n--- Test 2: Drive toward wall (expect slowdown) ---')
        self.get_logger().info('Driving forward at 0.4 m/s for 6 seconds...')
        self.cmd_vel_received.clear()
        self.send_nav_cmd(0.4, 0.0, 6.0)

        if len(self.cmd_vel_received) > 20:
            first_half = self.cmd_vel_received[:len(self.cmd_vel_received)//2]
            second_half = self.cmd_vel_received[len(self.cmd_vel_received)//2:]

            avg_first = sum(c['linear_x'] for c in first_half) / len(first_half)
            avg_second = sum(c['linear_x'] for c in second_half) / len(second_half)

            self.get_logger().info(f'  First half avg velocity:  {avg_first:.3f} m/s')
            self.get_logger().info(f'  Second half avg velocity: {avg_second:.3f} m/s')

            # As robot approaches wall, velocity should decrease.
            self.check(
                'Velocity decreased near obstacle',
                avg_second < avg_first or avg_second < 0.05,
                f'first={avg_first:.3f}, second={avg_second:.3f}',
            )

            # Check if robot eventually stopped or nearly stopped.
            last_vels = [c['linear_x'] for c in self.cmd_vel_received[-10:]]
            avg_last = sum(last_vels) / len(last_vels)
            self.check(
                'Robot stopped or slowed significantly near wall',
                avg_last < 0.15,
                f'avg of last 10 cmd_vel = {avg_last:.3f}',
            )
        else:
            self.check('Enough cmd_vel messages received', False,
                       f'only {len(self.cmd_vel_received)}')

        self.stop()
        time.sleep(1.0)

        # ---- Test 3: Check emergency stop distance ----
        self.get_logger().info('\n--- Test 3: Emergency stop check ---')
        front_dist = self.get_front_min_distance()
        self.get_logger().info(f'  Front distance after driving: {front_dist:.2f}m')

        self.check(
            'Robot did not crash into wall (distance > 0.2m)',
            front_dist > 0.2,
            f'front_dist = {front_dist:.2f}m',
        )

        # ---- Test 4: Rotation away from obstacle ----
        self.get_logger().info('\n--- Test 4: Rotation away from obstacle ---')
        self.get_logger().info('Sending forward velocity while close to wall...')
        self.cmd_vel_received.clear()
        self.send_nav_cmd(0.4, 0.0, 3.0)

        if self.cmd_vel_received:
            # Should see rotation commands (angular.z != 0) when very close.
            rotations = [abs(c['angular_z']) for c in self.cmd_vel_received
                         if abs(c['angular_z']) > 0.1]
            self.check(
                'Obstacle avoider issued rotation commands',
                len(rotations) > 0,
                f'{len(rotations)} rotation commands detected',
            )

        self.stop()
        time.sleep(1.0)

        # ---- Test 5: Reverse is not blocked ----
        self.get_logger().info('\n--- Test 5: Reverse not blocked by front obstacle ---')
        self.cmd_vel_received.clear()
        self.send_nav_cmd(-0.3, 0.0, 2.0)

        if self.cmd_vel_received:
            reverse_vels = [c['linear_x'] for c in self.cmd_vel_received]
            avg_reverse = sum(reverse_vels) / len(reverse_vels)
            self.check(
                'Reverse velocity passed through',
                avg_reverse < -0.1,
                f'avg reverse = {avg_reverse:.3f}',
            )

        self.stop()

        # ---- Summary ----
        self.get_logger().info('\n' + '=' * 60)
        total = self.pass_count + self.fail_count
        self.get_logger().info(
            f'Results: {self.pass_count}/{total} passed, '
            f'{self.fail_count}/{total} failed'
        )
        self.get_logger().info('=' * 60)

        return self.fail_count == 0


def main():
    rclpy.init()
    test = ObstacleAvoidanceTest()

    try:
        success = test.run_tests()
    except KeyboardInterrupt:
        test.get_logger().info('Test interrupted.')
        success = False
    finally:
        test.destroy_node()
        rclpy.shutdown()

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
