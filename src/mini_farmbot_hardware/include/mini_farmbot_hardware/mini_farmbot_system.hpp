#ifndef MINI_FARMBOT_HARDWARE__MINI_FARMBOT_SYSTEM_HPP_
#define MINI_FARMBOT_HARDWARE__MINI_FARMBOT_SYSTEM_HPP_

#include <array>
#include <cstdint>
#include <string>
#include <vector>

#include "hardware_interface/system_interface.hpp"
#include "hardware_interface/types/hardware_interface_return_values.hpp"
#include "rclcpp/duration.hpp"
#include "rclcpp/time.hpp"

namespace mini_farmbot_hardware
{

class MiniFarmbotSystem : public hardware_interface::SystemInterface
{
public:
  hardware_interface::CallbackReturn on_init(
    const hardware_interface::HardwareInfo & info) override;

  std::vector<hardware_interface::StateInterface> export_state_interfaces() override;
  std::vector<hardware_interface::CommandInterface> export_command_interfaces() override;

  hardware_interface::CallbackReturn on_activate(
    const rclcpp_lifecycle::State & previous_state) override;
  hardware_interface::CallbackReturn on_deactivate(
    const rclcpp_lifecycle::State & previous_state) override;

  hardware_interface::return_type read(
    const rclcpp::Time & time, const rclcpp::Duration & period) override;
  hardware_interface::return_type write(
    const rclcpp::Time & time, const rclcpp::Duration & period) override;

private:
  bool open_serial_port();
  void close_serial_port();
  bool send_line(const std::string & line);
  void process_serial_input();
  void process_serial_line(const std::string & line);
  long meters_to_steps(double position, std::size_t axis) const;
  double steps_to_meters(long steps, std::size_t axis) const;

  std::vector<double> positions_;
  std::vector<double> commands_;
  std::string device_;
  std::string receive_buffer_;
  std::array<double, 3> steps_per_meter_{{60000.0, 60000.0, 80000.0}};
  double max_speed_steps_per_second_{1000.0};
  std::array<long, 3> last_command_steps_{{0, 0, 0}};
  int serial_fd_{-1};
  int baud_rate_{115200};
  bool command_sent_{false};
  bool active_{false};
};

}  // namespace mini_farmbot_hardware

#endif  // MINI_FARMBOT_HARDWARE__MINI_FARMBOT_SYSTEM_HPP_