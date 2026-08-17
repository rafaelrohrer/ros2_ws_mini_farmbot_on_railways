import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, TimerAction
from launch.conditions import IfCondition
from launch.substitutions import Command, LaunchConfiguration, PythonExpression, IfElseSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    use_gazebo = LaunchConfiguration('use_gazebo')
    use_rviz = LaunchConfiguration('use_rviz')
    robot_variant = LaunchConfiguration('robot_variant')

    description_package_share = get_package_share_directory('mini_farmbot_description')
    launch_package_share = get_package_share_directory('launch_file')

    # Keep default mini-farmbot trajectory names intact for the controller flow,
    # but allow a matching Farmbot RViz-only visualization when robot_variant is set
    # to 0_FARMBOT.
    fake_joint_names = IfElseSubstitution(
        PythonExpression(["'", robot_variant, "' == '0_FARMBOT'"]),
        '[rail_left_to_vertical_leg_left, y_axis_to_y_to_z_connector, y_to_z_connector_to_z_axis]',
        '[rail_left_to_leg_front_left, y_axis_to_y_to_z_connector, y_to_z_connector_to_z_axis]'
    )
    
    # Determine which URDF xacro file to load based on robot_variant
    xacro_filename = IfElseSubstitution(
        PythonExpression(["'", robot_variant, "' == '0_FARMBOT'"]),
        '0_FARMBOT.urdf.xacro',
        '0_MINI_FARMBOT_ON_ALUMINIUM_PROFILES.urdf.xacro'
    )

    use_ros2_control = IfElseSubstitution(
        PythonExpression(["'", use_gazebo, "' == 'true'"]),
        'true',
        'false',
    )
    
    xacro_file_dir = os.path.join(
        description_package_share,
        'src',
    )
    
    rviz_config_file = os.path.join(
        launch_package_share,
        'config',
        'mini_farmbot_description.rviz',
    )
    robot_description = Command([
        'xacro ',
        xacro_file_dir,
        '/',
        xacro_filename,
        ' sim_mode:=true',
        ' use_ros2_control:=',
        use_ros2_control,
    ])

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
                    '-name', 'mini_farmbot_description',
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
            'joint_names': fake_joint_names,
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
            'robot_variant',
            default_value='0_MINI_FARMBOT',
            description='Robot variant to launch: 0_MINI_FARMBOT or 0_FARMBOT',
        ),
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
        DeclareLaunchArgument(
            'use_ros2_control',
            default_value='false',
            description='Explicitly enable ros2_control for controller-aware URDFs. Defaults to false for RViz-only visualization.',
        ),
        robot_state_publisher,
        gazebo,
        spawn_entity,
        spawn_joint_state_broadcaster,
        spawn_joint_trajectory_controller,
        fake_controller,
        rviz,
    ])
