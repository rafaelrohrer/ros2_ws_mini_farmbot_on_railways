from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import IfElseSubstitution, LaunchConfiguration, PythonExpression
from launch_ros.actions import Node


def generate_launch_description():
    robot_variant = LaunchConfiguration('robot_variant')
    controller_name = LaunchConfiguration('controller_name')
    joint_names = LaunchConfiguration('joint_names')
    positions = LaunchConfiguration('positions')
    duration_sec = LaunchConfiguration('duration_sec')
    start_fake_controller = LaunchConfiguration('start_fake_controller')
    yaml_file = LaunchConfiguration('yaml_file')

    variant_joint_names = IfElseSubstitution(
        PythonExpression(["'", robot_variant, "' == '0_FARMBOT'"]),
        '[rail_left_to_vertical_leg_left, y_axis_to_y_to_z_connector, y_to_z_connector_to_z_axis]',
        '[rail_left_to_leg_front_left, y_axis_to_y_to_z_connector, y_to_z_connector_to_z_axis]',
    )

    resolved_joint_names = IfElseSubstitution(
        PythonExpression(["'", joint_names, "' == ''"]),
        variant_joint_names,
        joint_names,
    )

    variant_yaml_file = IfElseSubstitution(
        PythonExpression(["'", robot_variant, "' == '0_FARMBOT'"]),
        'farmbot_controllers.yaml',
        'mini_farmbot_controllers.yaml',
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'robot_variant',
            default_value='0_MINI_FARMBOT_ON_ALUMINIUM_PROFILES',
            description='Robot variant to start: 0_MINI_FARMBOT_ON_ALUMINIUM_PROFILES or 0_FARMBOT',
        ),
        DeclareLaunchArgument(
            'controller_name',
            default_value='joint_trajectory_controller',
            description='Name of the JointTrajectoryController to target',
        ),
        DeclareLaunchArgument(
            'joint_names',
            default_value='',
            description='Optional explicit joint names as a YAML-style list; when empty, robot_variant decides the defaults',
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
        DeclareLaunchArgument(
            'yaml_file',
            default_value='mini_farmbot_controllers.yaml',
            description='ROS controller YAML file to use for the selected robot variant',
        ),
        DeclareLaunchArgument(
            'start_fake_controller',
            default_value='false',
            description='If true, start the fake controller for the selected robot variant',
        ),
        Node(
            package='mini_farmbot_control',
            executable='fake_joint_trajectory_controller',
            output='screen',
            parameters=[{
                'controller_name': controller_name,
                'joint_names': variant_joint_names,
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
                'joint_names': resolved_joint_names,
                'positions': positions,
                'duration_sec': duration_sec,
            }],
            condition=IfCondition(PythonExpression(["'", start_fake_controller, "' == 'false'"])),
        ),
        DeclareLaunchArgument(
            'variant_yaml_file',
            default_value='mini_farmbot_controllers.yaml',
            description='Deprecated convenience alias kept for compatibility',
        ),
    ])
