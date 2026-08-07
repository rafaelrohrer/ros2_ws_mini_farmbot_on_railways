from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    controller_name = LaunchConfiguration('controller_name')
    joint_names = LaunchConfiguration('joint_names')
    positions = LaunchConfiguration('positions')
    duration_sec = LaunchConfiguration('duration_sec')

    return LaunchDescription([
        DeclareLaunchArgument(
            'controller_name',
            default_value='joint_trajectory_controller',
            description='Name of the JointTrajectoryController',
        ),
        DeclareLaunchArgument(
            'joint_names',
            default_value='[base_link_to_leg_front_left, y_axis_to_y_to_z_connector, y_to_z_connector_to_z_axis]',
            description='Joint names as a YAML-style list',
        ),
        DeclareLaunchArgument(
            'positions',
            default_value='[0.2, 0.05, 0.05]',
            description='Target positions as a YAML-style list',
        ),
        DeclareLaunchArgument(
            'duration_sec',
            default_value='4.0',
            description='Trajectory duration in seconds',
        ),
        Node(
            package='mini_farmbot_control',
            executable='send_test_trajectory',
            output='screen',
            parameters=[{
                'controller_name': controller_name,
                'joint_names': joint_names,
                'positions': positions,
                'duration_sec': duration_sec,
            }],
        ),
    ])
