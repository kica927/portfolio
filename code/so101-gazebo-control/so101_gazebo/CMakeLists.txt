cmake_minimum_required(VERSION 3.8)
project(so101_gazebo)

find_package(ament_cmake REQUIRED)

install(DIRECTORY launch worlds config DESTINATION share/${PROJECT_NAME})
install(PROGRAMS scripts/track_test.py scripts/hold_test.py DESTINATION lib/${PROJECT_NAME})

ament_package()
