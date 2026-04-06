"""
Top-level launch file for the complete robocept robot.

Composes:
  1. Perception subsystem (LiDAR + camera + health monitor)
  2. Base controller (diff-drive motor driver)
  3. Static transforms (base_link → sensor frames)
"""

import yaml
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from ament_index_python.packages import get_package_share_directory
import os


def _load_static_transforms(config_path):
    """Load static transform definitions from YAML."""
    if not os.path.exists(config_path):
        return []

    with open(config_path, 'r') as f:
        data = yaml.safe_load(f) or {}

    nodes = []
    for tf in data.get('static_transforms', []):
        nodes.append(
            Node(
                package='tf2_ros',
                executable='static_transform_publisher',
                name=f'static_tf_{tf["child_frame"]}',
                arguments=[
                    '--x', str(tf.get('x', 0.0)),
                    '--y', str(tf.get('y', 0.0)),
                    '--z', str(tf.get('z', 0.0)),
                    '--roll', str(tf.get('roll', 0.0)),
                    '--pitch', str(tf.get('pitch', 0.0)),
                    '--yaw', str(tf.get('yaw', 0.0)),
                    '--frame-id', tf['parent_frame'],
                    '--child-frame-id', tf['child_frame'],
                ],
            )
        )
    return nodes


def generate_launch_description():
    system_dir = get_package_share_directory('robocept_system')

    # 1. Perception subsystem.
    perception = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([
                FindPackageShare('robocept_bringup'),
                'launch', 'perception.launch.py',
            ])
        ),
    )

    # 2. Base controller.
    base = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([
                FindPackageShare('robocept_base'),
                'launch', 'base.launch.py',
            ])
        ),
    )

    # 3. Static transforms.
    tf_config = os.path.join(system_dir, 'config', 'static_transforms.yaml')
    static_tfs = _load_static_transforms(tf_config)

    return LaunchDescription([
        perception,
        base,
    ] + static_tfs)
