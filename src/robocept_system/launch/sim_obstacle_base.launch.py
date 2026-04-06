"""Launch simulation, base controller adapter, obstacle avoidance, and sim health."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    use_sim_time = LaunchConfiguration('use_sim_time')
    headless = LaunchConfiguration('headless')
    with_health_monitor = LaunchConfiguration('with_health_monitor')

    use_sim_time_arg = DeclareLaunchArgument(
        'use_sim_time',
        default_value='true',
        description='Use Gazebo /clock for ROS nodes.',
    )
    headless_arg = DeclareLaunchArgument(
        'headless',
        default_value='true',
        description='Run Gazebo without the GUI.',
    )
    with_health_monitor_arg = DeclareLaunchArgument(
        'with_health_monitor',
        default_value='true',
        description='Launch the simulated perception health monitor.',
    )

    system_share = FindPackageShare('robocept_system')
    nav_share = FindPackageShare('robocept_nav')

    simulation = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([
                system_share, 'launch', 'sim_base.launch.py',
            ])
        ),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'headless': headless,
        }.items(),
    )

    obstacle_avoider = Node(
        package='robocept_nav',
        executable='obstacle_avoider',
        name='obstacle_avoider',
        namespace='robocept',
        parameters=[
            PathJoinSubstitution([nav_share, 'config', 'nav.yaml']),
            {'use_sim_time': use_sim_time},
        ],
        output='screen',
    )

    health_monitor = Node(
        package='robocept_health',
        executable='perception_health_monitor',
        name='perception_health_monitor',
        namespace='robocept',
        parameters=[
            PathJoinSubstitution([
                system_share, 'config', 'health_monitor_sim.yaml'
            ]),
            {'use_sim_time': use_sim_time},
        ],
        condition=IfCondition(with_health_monitor),
        output='screen',
    )

    return LaunchDescription([
        use_sim_time_arg,
        headless_arg,
        with_health_monitor_arg,
        simulation,
        obstacle_avoider,
        health_monitor,
    ])
