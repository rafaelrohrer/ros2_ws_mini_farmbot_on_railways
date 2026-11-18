from __future__ import annotations

import math
import time
from typing import List

import rclpy
from control_msgs.action import FollowJointTrajectory
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.node import Node
from sensor_msgs.msg import JointState


class FakeJointTrajectoryController(Node):
    def __init__(self) -> None:
        super().__init__('fake_joint_trajectory_controller')

        self.declare_parameter('controller_name', 'joint_trajectory_controller')
        self.declare_parameter(
            'joint_names',
            ['x_joint', 'y_joint', 'z_joint'],
        )
        self.declare_parameter('publish_rate_hz', 20.0)
        self.declare_parameter('default_positions', [0.0, 0.0, 0.0])

        self._controller_name = str(self.get_parameter('controller_name').value)
        self._joint_names: List[str] = list(self.get_parameter('joint_names').value)
        self._publish_rate_hz = float(self.get_parameter('publish_rate_hz').value)
        self._current_positions: List[float] = [float(value) for value in self.get_parameter('default_positions').value]
        self._target_positions: List[float] = list(self._current_positions)
        self._active_goal = False
        self._cancel_requested = False

        if len(self._joint_names) != len(self._current_positions):
            raise ValueError('joint_names and default_positions must have the same length')

        self._publisher = self.create_publisher(JointState, '/joint_states', 10)
        self._action_server = ActionServer(
            self,
            FollowJointTrajectory,
            f'/{self._controller_name}/follow_joint_trajectory',
            goal_callback=self._goal_callback,
            cancel_callback=self._cancel_callback,
            execute_callback=self._execute_callback,
        )

        timer_period = 1.0 / self._publish_rate_hz if self._publish_rate_hz > 0.0 else 0.05
        self._timer = self.create_timer(timer_period, self._publish_current_state)
        self._publish_current_state()

        self.get_logger().info(
            f'Fake controller ready on /{self._controller_name}/follow_joint_trajectory'
        )

    def _goal_callback(self, goal_request: FollowJointTrajectory.Goal) -> GoalResponse:
        if list(goal_request.trajectory.joint_names) != self._joint_names:
            self.get_logger().error(
                f'Rejecting trajectory with joint_names={list(goal_request.trajectory.joint_names)}'
            )
            return GoalResponse.REJECT

        if not goal_request.trajectory.points:
            self.get_logger().error('Rejecting empty trajectory')
            return GoalResponse.REJECT

        return GoalResponse.ACCEPT

    def _cancel_callback(self, _goal_handle) -> CancelResponse:
        self._cancel_requested = True
        return CancelResponse.ACCEPT

    def _execute_callback(self, goal_handle):
        self._active_goal = True
        self._cancel_requested = False

        trajectory = goal_handle.request.trajectory
        final_point = trajectory.points[-1]
        if len(final_point.positions) != len(self._joint_names):
            goal_handle.abort()
            self._active_goal = False
            result = FollowJointTrajectory.Result()
            result.error_code = FollowJointTrajectory.Result.INVALID_GOAL
            result.error_string = 'Position vector length does not match joint_names'
            return result

        start_positions = list(self._current_positions)
        self._target_positions = [float(value) for value in final_point.positions]
        duration_sec = float(final_point.time_from_start.sec) + float(final_point.time_from_start.nanosec) / 1e9
        duration_sec = max(duration_sec, 0.0)
        steps = max(int(duration_sec * self._publish_rate_hz), 1)
        step_time = duration_sec / steps if duration_sec > 0.0 else 0.0

        self.get_logger().info(
            f'Executing fake trajectory for joints {self._joint_names} to {self._target_positions}'
        )

        for step in range(steps):
            if self._cancel_requested or goal_handle.is_cancel_requested:
                goal_handle.canceled()
                self._active_goal = False
                result = FollowJointTrajectory.Result()
                result.error_code = FollowJointTrajectory.Result.SUCCESSFUL
                result.error_string = 'Trajectory canceled'
                return result

            progress = float(step + 1) / float(steps)
            self._current_positions = [
                start + (target - start) * progress
                for start, target in zip(start_positions, self._target_positions)
            ]
            self._publish_current_state()
            if step_time > 0.0:
                time.sleep(step_time)

        self._current_positions = list(self._target_positions)
        self._publish_current_state()
        goal_handle.succeed()
        self._active_goal = False

        result = FollowJointTrajectory.Result()
        result.error_code = FollowJointTrajectory.Result.SUCCESSFUL
        result.error_string = ''
        return result

    def _publish_current_state(self) -> None:
        message = JointState()
        message.header.stamp = self.get_clock().now().to_msg()
        message.name = self._joint_names
        message.position = list(self._current_positions)
        self._publisher.publish(message)


def main() -> None:
    rclpy.init()
    node = FakeJointTrajectoryController()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
