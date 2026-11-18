from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    # Die Gelenknamen (x_joint, y_joint, z_joint) sind in allen Robotervarianten gleich
    # und als Default in den Nodes hinterlegt. Deshalb braucht es hier keine Variantenweiche.
    controller_name = LaunchConfiguration('controller_name')
    positions = LaunchConfiguration('positions')
    duration_sec = LaunchConfiguration('duration_sec')
    start_fake_controller = LaunchConfiguration('start_fake_controller')

    return LaunchDescription([
        DeclareLaunchArgument(
            'controller_name',
            default_value='joint_trajectory_controller',
            description='Name of the JointTrajectoryController to target',
        ),
        DeclareLaunchArgument(
            'positions',
            default_value='[0.2, 0.05, 0.05]',
            description='Target positions for x_joint, y_joint, z_joint as a YAML-style list',
        ),
        DeclareLaunchArgument(
            'duration_sec',
            default_value='4.0',
            description='Trajectory duration in seconds',
        ),
        DeclareLaunchArgument(
            'start_fake_controller',
            default_value='false',
            description='If true, start the fake controller instead of sending a trajectory',
        ),
        Node(
            package='mini_farmbot_control',
            executable='fake_joint_trajectory_controller',
            output='screen',
            parameters=[{
                'controller_name': controller_name,
                'publish_rate_hz': 20.0,
                'default_positions': [0.0, 0.0, 0.0],
            }],
            condition=IfCondition(start_fake_controller),
        ),
        Node(
            package='mini_farmbot_control',
            executable='send_test_trajectory',
            output='screen',
            parameters=[{
                'controller_name': controller_name,
                'positions': positions,
                'duration_sec': duration_sec,
            }],
            condition=UnlessCondition(start_fake_controller),
        ),
    ])
