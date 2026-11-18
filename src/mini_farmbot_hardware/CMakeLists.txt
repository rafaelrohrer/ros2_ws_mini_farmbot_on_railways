cmake_minimum_required(VERSION 3.8)
project(mini_farmbot_hardware)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(hardware_interface REQUIRED)
find_package(pluginlib REQUIRED)
find_package(rclcpp REQUIRED)

add_library(mini_farmbot_system SHARED
  src/mini_farmbot_system.cpp
)

target_include_directories(mini_farmbot_system PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>
)

ament_target_dependencies(mini_farmbot_system
  hardware_interface
  pluginlib
  rclcpp
)

pluginlib_export_plugin_description_file(hardware_interface mini_farmbot_hardware.xml)

install(
  TARGETS mini_farmbot_system
  EXPORT export_mini_farmbot_system
  ARCHIVE DESTINATION lib
  LIBRARY DESTINATION lib
  RUNTIME DESTINATION bin
)

install(
  DIRECTORY include/
  DESTINATION include
)

install(
  DIRECTORY config launch
  DESTINATION share/${PROJECT_NAME}
)

install(
  FILES mini_farmbot_hardware.xml
  DESTINATION share/${PROJECT_NAME}
)

ament_export_targets(export_mini_farmbot_system HAS_LIBRARY_TARGET)
ament_export_dependencies(hardware_interface pluginlib rclcpp)

ament_package()