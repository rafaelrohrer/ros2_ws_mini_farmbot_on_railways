from __future__ import annotations

from typing import List

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node

from control_msgs.action import FollowJointTrajectory
from trajectory_msgs.msg import JointTrajectoryPoint


class JointTrajectory1Client(Node):
    def __init__(self) -> None:
        super().__init__('joint_trajectory_1_client')

        self.declare_parameter('controller_name', 'joint_trajectory_controller')
        self.declare_parameter(
            'joint_names',
            [
                'base_link_to_leg_front_left',
                'base_link_to_leg_front_right',
                'y_axis_to_y_to_z_connector',
                'y_to_z_connector_to_z_axis',
            ],
        )
        self.declare_parameter('positions', [0.2, 0.2, 0.05, 0.05])
        self.declare_parameter('duration_sec', 4.0)

        controller_name = self.get_parameter('controller_name').value
        self._joint_names: List[str] = list(self.get_parameter('joint_names').value)
        self._positions: List[float] = [float(value) for value in self.get_parameter('positions').value]
        self._duration_sec = float(self.get_parameter('duration_sec').value)

        if len(self._joint_names) != len(self._positions):
            raise ValueError('joint_names and positions must have the same length')

        action_name = f'/{controller_name}/follow_joint_trajectory'
        self._client = ActionClient(self, FollowJointTrajectory, action_name)
        self.get_logger().info(f'Waiting for action server: {action_name}')

    def send_goal(self) -> None:
        if not self._client.wait_for_server(timeout_sec=10.0):
            self.get_logger().error('Trajectory action server not available')
            rclpy.shutdown()
            return

        goal = FollowJointTrajectory.Goal()
        goal.trajectory.joint_names = self._joint_names

        point = JointTrajectoryPoint()
        point.positions = self._positions
        point.time_from_start.sec = int(self._duration_sec)
        point.time_from_start.nanosec = int((self._duration_sec - int(self._duration_sec)) * 1e9)
        goal.trajectory.points = [point]

        self.get_logger().info(
            f'Sending trajectory for joints {self._joint_names} with positions {self._positions}'
        )

        send_goal_future = self._client.send_goal_async(goal, feedback_callback=self._feedback_callback)
        send_goal_future.add_done_callback(self._goal_response_callback)

    def _feedback_callback(self, feedback_msg: FollowJointTrajectory.FeedbackMessage) -> None:
        self.get_logger().debug(f'Feedback: {feedback_msg.feedback}')

    def _goal_response_callback(self, future) -> None:
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().error('Trajectory goal rejected')
            rclpy.shutdown()
            return

        self.get_logger().info('Trajectory goal accepted')
        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(self._result_callback)

    def _result_callback(self, future) -> None:
        result = future.result().result
        self.get_logger().info(f'Trajectory execution finished with error_code={result.error_code}')
        rclpy.shutdown()


def main() -> None:
    rclpy.init()
    node = JointTrajectory1Client()
    node.send_goal()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
