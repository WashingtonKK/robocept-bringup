"""
Launch robocept simulation in Ignition Gazebo (Fortress).

Starts:
  1. Ignition Gazebo with the test world
  2. Robot state publisher (URDF → TF)
  3. Spawn robot in Ignition
  4. ros_gz_bridge (bridges Ignition topics ↔ ROS 2 topics)

After launch, drive with:
  ros2 run teleop_twist_keyboard teleop_twist_keyboard
"""

import os

from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    SetEnvironmentVariable,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    system_dir = get_package_share_directory('robocept_system')
    urdf_path = os.path.join(system_dir, 'urdf', 'robocept.urdf.xacro')
    world_path = os.path.join(system_dir, 'worlds', 'robocept_test.sdf')

    # Arguments.
    use_sim_time = DeclareLaunchArgument(
        'use_sim_time', default_value='true',
    )
    headless = DeclareLaunchArgument(
        'headless', default_value='true',
        description='Run Ignition without GUI (for headless Jetson)',
    )

    # Set IGN resource path so Ignition can find our models.
    ign_resource_path = SetEnvironmentVariable(
        'IGN_GAZEBO_RESOURCE_PATH',
        os.path.join(system_dir, 'worlds'),
    )

    # 1. Ignition Gazebo.
    ign_gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([
                FindPackageShare('ros_gz_sim'),
                'launch', 'gz_sim.launch.py',
            ])
        ),
        launch_arguments={
            'gz_args': ['-r -s ', world_path],  # -s = server only (headless)
        }.items(),
    )

    # 2. Robot state publisher.
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[{
            'robot_description': ParameterValue(
                Command(['xacro ', urdf_path]), value_type=str
            ),
            'use_sim_time': LaunchConfiguration('use_sim_time'),
        }],
        output='screen',
    )

    # 3. Spawn robot.
    spawn_robot = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=[
            '-topic', 'robot_description',
            '-name', 'robocept',
            '-x', '0.0',
            '-y', '0.0',
            '-z', '0.05',
        ],
        output='screen',
    )

    # 4. ros_gz_bridge: bridge Ignition topics to ROS 2.
    # Format: ign_topic@ros_msg_type[ign_msg_type]
    # Directions: @ = bidirectional, @...[ = IGN→ROS, ]...@ = ROS→IGN
    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=[
            # cmd_vel: ROS → IGN
            '/cmd_vel@geometry_msgs/msg/Twist]ignition.msgs.Twist',
            # odom: IGN → ROS
            '/odom@nav_msgs/msg/Odometry[ignition.msgs.Odometry',
            # LiDAR: IGN → ROS
            '/lidar/scan@sensor_msgs/msg/LaserScan[ignition.msgs.LaserScan',
            # RGB camera: IGN → ROS
            '/camera/image@sensor_msgs/msg/Image[ignition.msgs.Image',
            '/camera/camera_info@sensor_msgs/msg/CameraInfo[ignition.msgs.CameraInfo',
            # Depth camera: IGN → ROS
            '/camera/depth_image@sensor_msgs/msg/Image[ignition.msgs.Image',
            # TF: IGN → ROS
            '/tf@tf2_msgs/msg/TFMessage[ignition.msgs.Pose_V',
            # Clock: IGN → ROS
            '/clock@rosgraph_msgs/msg/Clock[ignition.msgs.Clock',
        ],
        remappings=[
            ('/lidar/scan', '/robocept/lidar/scan'),
            ('/camera/image', '/robocept/camera/color/image_raw'),
            ('/camera/camera_info', '/robocept/camera/color/camera_info'),
            ('/camera/depth_image', '/robocept/camera/depth/image_rect_raw'),
        ],
        parameters=[{
            'use_sim_time': LaunchConfiguration('use_sim_time'),
        }],
        output='screen',
    )

    return LaunchDescription([
        use_sim_time,
        headless,
        ign_resource_path,
        ign_gazebo,
        robot_state_publisher,
        spawn_robot,
        bridge,
    ])
