#!/usr/bin/env python3
# TurtleBot3 + Gazebo Classic + 3D LiDAR (Humble対応: init→factory の順でロード)
import os

from ament_index_python.packages import (
    get_package_share_directory,
    get_package_prefix,
)
from launch import LaunchDescription
from launch.actions import (
    IncludeLaunchDescription,
    DeclareLaunchArgument,
    SetEnvironmentVariable,
    ExecuteProcess,
    LogInfo,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():
    pkg_tb3_gz = get_package_share_directory('turtlebot3_gazebo')
    aws_small_warehouse_dir = get_package_share_directory('aws_robomaker_small_warehouse_world')

    # Gazebo ROS プラグインの場所
    gazebo_ros_prefix = get_package_prefix('gazebo_ros')   # 例: /opt/ros/humble
    plugin_dir = os.path.join(gazebo_ros_prefix, 'lib')

    # init/api プラグインは環境により名前が異なる（Humbleは init が多い）
    api_candidates = [
        'libgazebo_ros_api_plugin.so',  # あればこれ
        'libgazebo_ros_init.so',        # 無ければこれ（Humbleで一般的）
    ]
    selected_api_plugin = None
    for c in api_candidates:
        p = os.path.join(plugin_dir, c)
        if os.path.exists(p):
            selected_api_plugin = p
            break

    factory_plugin = os.path.join(plugin_dir, 'libgazebo_ros_factory.so')

    # 起動引数
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    x_pose = LaunchConfiguration('x_pose', default='-2.0')
    y_pose = LaunchConfiguration('y_pose', default='-0.5')
    world_path_default = os.path.join(aws_small_warehouse_dir, 'worlds', 'no_roof_small_warehouse', 'no_roof_small_warehouse.world')
    world = LaunchConfiguration('world', default=world_path_default)

    # Gazebo Classic を生コマンドで起動（★順番: init/api → factory）
    gzserver_cmd = ['gzserver', '--verbose', world]
    if selected_api_plugin:
        gzserver_cmd += ['-s', selected_api_plugin]
    gzserver_cmd += ['-s', factory_plugin]

    gzserver = ExecuteProcess(cmd=gzserver_cmd, output='screen')
    gzclient = ExecuteProcess(cmd=['gzclient'], output='screen')

    # robot_state_publisher（TF配信用）
    robot_state_publisher_cmd = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_tb3_gz, 'launch', 'robot_state_publisher.launch.py')
        ),
        launch_arguments={'use_sim_time': use_sim_time}.items()
    )

    # 3D LiDAR組み込みURDFをそのままspawn
    urdf_path = os.path.join(pkg_tb3_gz, 'urdf', 'turtlebot3_waffle_3dlidar_planar.urdf')
    spawn_tb3_from_urdf = Node(
        package='gazebo_ros',
        executable='spawn_entity.py',
        arguments=['-entity', 'tb3_3dlidar', '-file', urdf_path, '-x', x_pose, '-y', y_pose],
        output='screen'
    )

    set_gazebo_asset_path = SetEnvironmentVariable(
        'GAZEBO_MODEL_PATH',
        os.pathsep.join([
            os.path.join(pkg_tb3_gz, 'models'),
            os.path.join(aws_small_warehouse_dir, 'models')
        ])
    )

    ld = LaunchDescription()
    ld.add_action(DeclareLaunchArgument('use_sim_time', default_value='true'))
    ld.add_action(DeclareLaunchArgument('x_pose', default_value='-2.0'))
    ld.add_action(DeclareLaunchArgument('y_pose', default_value='-0.5'))
    ld.add_action(DeclareLaunchArgument('world', default_value=world_path_default))
    ld.add_action(set_gazebo_asset_path)
    ld.add_action(gzserver)
    ld.add_action(gzclient)
    ld.add_action(robot_state_publisher_cmd)
    ld.add_action(spawn_tb3_from_urdf)

    return ld
