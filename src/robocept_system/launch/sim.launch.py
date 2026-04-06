"""
Launch the full robocept simulation in Gazebo.

Starts:
  1. Gazebo with the test world
  2. Robot state publisher (URDF → TF)
  3. Robot spawner (places robot in Gazebo)
  4. Health monitor (monitors simulated sensor topics)
  5. Navigation stack (obstacle avoidance + waypoint nav)

After launch, drive with:
  ros2 run teleop_twist_keyboard teleop_twist_keyboard
"""

import os

from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    ExecuteProcess,
    IncludeLaunchDescription,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import (
    Command,
    LaunchConfiguration,
    PathJoinSubstitution,
)
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    system_dir = get_package_share_directory('robocept_system')

    # Arguments.
    world_arg = DeclareLaunchArgument(
        'world',
        default_value=os.path.join(system_dir, 'worlds', 'robocept_test.world'),
        description='Path to Gazebo world file',
    )

    use_sim_time = DeclareLaunchArgument(
        'use_sim_time', default_value='true',
        description='Use simulation time',
    )

    # 1. Gazebo.
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([
                FindPackageShare('gazebo_ros'),
                'launch', 'gazebo.launch.py',
            ])
        ),
        launch_arguments={
            'world': LaunchConfiguration('world'),
        }.items(),
    )

    # 2. Robot state publisher (URDF → TF).
    urdf_path = os.path.join(system_dir, 'urdf', 'robocept.urdf.xacro')
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[{
            'robot_description': Command(['xacro ', urdf_path]),
            'use_sim_time': LaunchConfiguration('use_sim_time'),
        }],
        output='screen',
    )

    # 3. Spawn robot in Gazebo.
    spawn_robot = Node(
        package='gazebo_ros',
        executable='spawn_entity.py',
        arguments=[
            '-topic', 'robot_description',
            '-entity', 'robocept',
            '-x', '0.0',
            '-y', '0.0',
            '-z', '0.05',
        ],
        output='screen',
    )

    # 4. Health monitor (optional, monitors sim topics).
    health_monitor = Node(
        package='robocept_health',
        executable='perception_health_monitor',
        name='perception_health_monitor',
        namespace='robocept',
        parameters=[
            os.path.join(system_dir, 'config', 'health_monitor_sim.yaml'),
            {'use_sim_time': LaunchConfiguration('use_sim_time')},
        ],
        output='screen',
    )

    # 5. Navigation (obstacle avoidance).
    nav_nodes = []
    try:
        nav_config = os.path.join(
            get_package_share_directory('robocept_nav'),
            'config', 'nav.yaml',
        )
        nav_nodes.append(Node(
            package='robocept_nav',
            executable='obstacle_avoider',
            name='obstacle_avoider',
            namespace='robocept',
            parameters=[
                nav_config,
                {'use_sim_time': LaunchConfiguration('use_sim_time')},
            ],
            output='screen',
        ))
    except Exception:
        pass  # robocept_nav not built yet — skip

    return LaunchDescription([
        world_arg,
        use_sim_time,
        gazebo,
        robot_state_publisher,
        spawn_robot,
        health_monitor,
    ] + nav_nodes)
