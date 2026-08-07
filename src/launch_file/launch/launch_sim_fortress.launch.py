import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, TimerAction
from launch.conditions import IfCondition
from launch.substitutions import Command, LaunchConfiguration, PythonExpression
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    use_gazebo = LaunchConfiguration('use_gazebo')
    use_rviz = LaunchConfiguration('use_rviz')

    description_package_share = get_package_share_directory('mini_farmbot')
    launch_package_share = get_package_share_directory('launch_file')
    xacro_file = os.path.join(
        description_package_share,
        'description',
        '0_MINI_FARMBOT_ON_ALUMINIUM_PROFILES.urdf.xacro',
    )
    rviz_config_file = os.path.join(
        launch_package_share,
        'config',
        'mini_farmbot.rviz',
    )
    robot_description = Command(['xacro ', xacro_file, ' sim_mode:=true'])

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[{
            'robot_description': ParameterValue(robot_description, value_type=str),
            'use_sim_time': ParameterValue(use_gazebo, value_type=bool),
        }],
    )

    gazebo = ExecuteProcess(
        cmd=['ign', 'gazebo', '-r'],
        additional_env={
            'LIBGL_ALWAYS_SOFTWARE': '1',
            'MESA_LOADER_DRIVER_OVERRIDE': 'llvmpipe',
            'GALLIUM_DRIVER': 'llvmpipe',
        },
        output='screen',
        condition=IfCondition(use_gazebo),
    )

    spawn_entity = TimerAction(
        period=5.0,
        actions=[
            ExecuteProcess(
                cmd=[
                    'ros2', 'run', 'ros_gz_sim', 'create',
                    '-name', 'mini_farmbot',
                    '-topic', 'robot_description',
                ],
                output='screen',
            )
        ],
        condition=IfCondition(use_gazebo),
    )

    spawn_joint_state_broadcaster = TimerAction(
        period=10.0,
        actions=[
            Node(
                package='controller_manager',
                executable='spawner',
                arguments=[
                    'joint_state_broadcaster',
                    '--controller-manager',
                    '/controller_manager',
                    '--controller-manager-timeout',
                    '120',
                ],
                output='screen',
            )
        ],
        condition=IfCondition(use_gazebo),
    )

    spawn_joint_trajectory_controller = TimerAction(
        period=12.0,
        actions=[
            Node(
                package='controller_manager',
                executable='spawner',
                arguments=[
                    'joint_trajectory_controller',
                    '--controller-manager',
                    '/controller_manager',
                    '--controller-manager-timeout',
                    '120',
                ],
                output='screen',
            )
        ],
        condition=IfCondition(use_gazebo),
    )

    fake_controller = Node(
        package='mini_farmbot_control',
        executable='fake_joint_trajectory_controller',
        output='screen',
        parameters=[{
            'use_sim_time': ParameterValue(use_gazebo, value_type=bool),
        }],
        condition=IfCondition(PythonExpression(["'", use_rviz, "' == 'true' and '", use_gazebo, "' == 'false'"])),
    )

    rviz = Node(
        package='rviz2',
        executable='rviz2',
        output='screen',
        arguments=['-d', rviz_config_file],
        parameters=[{
            'use_sim_time': ParameterValue(use_gazebo, value_type=bool),
        }],
        condition=IfCondition(use_rviz),
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_gazebo',
            default_value='true',
            description='Launch Gazebo and controllers when true',
        ),
        DeclareLaunchArgument(
            'use_rviz',
            default_value='true',
            description='Launch RViz when true',
        ),
        robot_state_publisher,
        gazebo,
        spawn_entity,
        spawn_joint_state_broadcaster,
        spawn_joint_trajectory_controller,
        fake_controller,
        rviz,
    ])
