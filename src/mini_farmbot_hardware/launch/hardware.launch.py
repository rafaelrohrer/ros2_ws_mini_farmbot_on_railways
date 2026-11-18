import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    description_share = get_package_share_directory('mini_farmbot_description')
    xacro_file = os.path.join(
        description_share, 'src', '0_MINI_FARMBOT_ON_ALUMINIUM_PROFILES.urdf.xacro'
    )
    controllers_file = os.path.join(description_share, 'config', 'controllers.yaml')

    device = LaunchConfiguration('device')

    # Die Hardware-Parameter (Port, Baudrate, steps_per_meter) stehen in ros2_control.xacro.
    # Der serielle Port wird hier als Xacro-Argument bis in das <param>-Feld des Plugins durchgereicht.
    robot_description = ParameterValue(
        Command([
            'xacro ', xacro_file,
            ' sim_mode:=false use_ros2_control:=true use_arduino_hardware:=true',
            ' device:=', device,
        ]),
        value_type=str,
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'device',
            default_value='/dev/ttyACM0',
            description='Serieller Port des Arduino Mega (z.B. /dev/ttyACM0 oder /dev/ttyUSB0)',
        ),
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            parameters=[{'robot_description': robot_description}],
            output='screen',
        ),
        Node(
            package='controller_manager',
            executable='ros2_control_node',
            parameters=[
                {'robot_description': robot_description},
                controllers_file,
                # Muss nach controllers_file stehen: Der echte Roboter hat keine Simulationsuhr,
                # deshalb wird use_sim_time aus der (auch für Gazebo genutzten) YAML überschrieben.
                {'use_sim_time': False},
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
