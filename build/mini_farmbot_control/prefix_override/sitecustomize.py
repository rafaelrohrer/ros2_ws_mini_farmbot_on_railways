import sys
if sys.prefix == '/usr':
    sys.real_prefix = sys.prefix
    sys.prefix = sys.exec_prefix = '/home/rafaelrohrer/bachelor_meilenstein_2/ros2_ws_mini_farmbot_on_railways/install/mini_farmbot_control'
