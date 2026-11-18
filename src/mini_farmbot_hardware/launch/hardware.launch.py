import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    description_share = get_package_share_directory('mini_farmbot_description')
    hardware_share = get_package_share_directory('mini_farmbot_hardware')
    xacro_file = os.path.join(
        description_share, 'src', '0_MINI_FARMBOT_ON_ALUMINIUM_PROFILES.urdf.xacro'
    )
    controllers_file = os.path.join(
        description_share, 'config', 'mini_farmbot_controllers.yaml'
    )
    hardware_file = os.path.join(hardware_share, 'config', 'hardware.yaml')

    robot_description = Command([
        'xacro ', xacro_file,
        ' sim_mode:=false use_ros2_control:=true use_arduino_hardware:=true',
    ])

    return LaunchDescription([
        DeclareLaunchArgument('device', default_value='/dev/ttyACM0'),
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            parameters=[{'robot_description': ParameterValue(robot_description, value_type=str)}],
            output='screen',
        ),
        Node(
            package='controller_manager',
            executable='ros2_control_node',
            parameters=[
                {'robot_description': ParameterValue(robot_description, value_type=str)},
                controllers_file,
                hardware_file,
                {'device': LaunchConfiguration('device')},
            ],
            remappings=[('robot_description', '/robot_description')],
            output='screen',
        ),
        Node(
            package='controller_manager',
            executable='spawner',
            arguments=['joint_state_broadcaster', '--controller-manager', '/controller_manager'],
            output='screen',
        ),
        Node(
            package='controller_manager',
            executable='spawner',
            arguments=['joint_trajectory_controller', '--controller-manager', '/controller_manager'],
            output='screen',
        ),
    ])