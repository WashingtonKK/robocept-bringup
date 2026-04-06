"""Launch Gazebo Sim with the base controller path in the loop."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    use_sim_time = LaunchConfiguration('use_sim_time')
    headless = LaunchConfiguration('headless')

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

    simulation = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([
                FindPackageShare('robocept_system'),
                'launch',
                'sim.launch.py',
            ])
        ),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'headless': headless,
            'drive_cmd_topic': '/robocept/base/drive_cmd',
            'odom_topic': '/robocept/base/sim_odom',
        }.items(),
    )

    base_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([
                FindPackageShare('robocept_base'),
                'launch',
                'base_sim.launch.py',
            ])
        ),
        launch_arguments={
            'use_sim_time': use_sim_time,
        }.items(),
    )

    return LaunchDescription([
        use_sim_time_arg,
        headless_arg,
        simulation,
        base_sim,
    ])
