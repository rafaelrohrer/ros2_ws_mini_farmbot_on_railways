#include "mini_farmbot_hardware/mini_farmbot_system.hpp"

#include <cerrno>
#include <fcntl.h>
#include <sstream>
#include <stdexcept>
#include <termios.h>
#include <unistd.h>
#include <utility>

#include "hardware_interface/types/hardware_interface_type_values.hpp"
#include "pluginlib/class_list_macros.hpp"

namespace mini_farmbot_hardware
{

hardware_interface::CallbackReturn MiniFarmbotSystem::on_init(
  const hardware_interface::HardwareInfo & info)
{
  if (hardware_interface::SystemInterface::on_init(info) !=
    hardware_interface::CallbackReturn::SUCCESS)
  {
    return hardware_interface::CallbackReturn::ERROR;
  }

  positions_.assign(info.joints.size(), 0.0);
  commands_.assign(info.joints.size(), 0.0);

  const auto device = info.hardware_parameters.find("device");
  if (device != info.hardware_parameters.end()) {
    device_ = device->second;
  } else {
    device_ = "/dev/ttyACM0";
  }

  const auto baud_rate = info.hardware_parameters.find("baud_rate");
  if (baud_rate != info.hardware_parameters.end()) {
    baud_rate_ = std::stoi(baud_rate->second);
  }

  const char * step_parameter_names[] = {
    "x_steps_per_meter", "y_steps_per_meter", "z_steps_per_meter"};
  for (std::size_t index = 0; index < steps_per_meter_.size(); ++index) {
    const auto parameter = info.hardware_parameters.find(step_parameter_names[index]);
    if (parameter != info.hardware_parameters.end()) {
      steps_per_meter_[index] = std::stod(parameter->second);
    }
  }

  const auto max_speed = info.hardware_parameters.find("max_speed_steps_per_second");
  if (max_speed != info.hardware_parameters.end()) {
    max_speed_steps_per_second_ = std::stod(max_speed->second);
  }

  return hardware_interface::CallbackReturn::SUCCESS;
}

std::vector<hardware_interface::StateInterface> MiniFarmbotSystem::export_state_interfaces()
{
  std::vector<hardware_interface::StateInterface> state_interfaces;
  for (std::size_t index = 0; index < info_.joints.size(); ++index) {
    state_interfaces.emplace_back(
      info_.joints[index].name, hardware_interface::HW_IF_POSITION, &positions_[index]);
  }
  return state_interfaces;
}

std::vector<hardware_interface::CommandInterface> MiniFarmbotSystem::export_command_interfaces()
{
  std::vector<hardware_interface::CommandInterface> command_interfaces;
  for (std::size_t index = 0; index < info_.joints.size(); ++index) {
    command_interfaces.emplace_back(
      info_.joints[index].name, hardware_interface::HW_IF_POSITION, &commands_[index]);
  }
  return command_interfaces;
}

hardware_interface::CallbackReturn MiniFarmbotSystem::on_activate(
  const rclcpp_lifecycle::State &)
{
  if (!open_serial_port()) {
    return hardware_interface::CallbackReturn::ERROR;
  }

  commands_ = positions_;
  command_sent_ = false;
  active_ = true;
  send_line("PING");
  return hardware_interface::CallbackReturn::SUCCESS;
}

hardware_interface::CallbackReturn MiniFarmbotSystem::on_deactivate(
  const rclcpp_lifecycle::State &)
{
  active_ = false;
  send_line("STOP");
  close_serial_port();
  return hardware_interface::CallbackReturn::SUCCESS;
}

hardware_interface::return_type MiniFarmbotSystem::read(
  const rclcpp::Time &, const rclcpp::Duration &)
{
  if (!active_) {
    return hardware_interface::return_type::ERROR;
  }

  process_serial_input();
  return hardware_interface::return_type::OK;
}

hardware_interface::return_type MiniFarmbotSystem::write(
  const rclcpp::Time &, const rclcpp::Duration &)
{
  if (!active_) {
    return hardware_interface::return_type::ERROR;
  }

  if (commands_.size() < 3) {
    return hardware_interface::return_type::ERROR;
  }

  std::array<long, 3> target_steps{};
  for (std::size_t index = 0; index < target_steps.size(); ++index) {
    target_steps[index] = meters_to_steps(commands_[index], index);
  }

  if (!command_sent_ || target_steps != last_command_steps_) {
    std::ostringstream command;
    command << "MOVE " << target_steps[0] << ' ' << target_steps[1] << ' '
            << target_steps[2] << ' ' << max_speed_steps_per_second_ << " 1";
    if (!send_line(command.str())) {
      return hardware_interface::return_type::ERROR;
    }
    last_command_steps_ = target_steps;
    command_sent_ = true;
  }

  return hardware_interface::return_type::OK;
}

bool MiniFarmbotSystem::open_serial_port()
{
  serial_fd_ = open(device_.c_str(), O_RDWR | O_NOCTTY | O_NONBLOCK);
  if (serial_fd_ < 0) {
    return false;
  }

  termios settings{};
  if (tcgetattr(serial_fd_, &settings) != 0) {
    close_serial_port();
    return false;
  }

  cfmakeraw(&settings);
  speed_t speed = B115200;
  switch (baud_rate_) {
    case 9600: speed = B9600; break;
    case 19200: speed = B19200; break;
    case 38400: speed = B38400; break;
    case 57600: speed = B57600; break;
    case 115200: speed = B115200; break;
    default:
      close_serial_port();
      return false;
  }
  cfsetispeed(&settings, speed);
  cfsetospeed(&settings, speed);
  settings.c_cflag |= (CLOCAL | CREAD);
  settings.c_cflag &= ~CSTOPB;
  settings.c_cflag &= ~CRTSCTS;
  settings.c_cflag &= ~CSIZE;
  settings.c_cflag |= CS8;
  settings.c_cc[VMIN] = 0;
  settings.c_cc[VTIME] = 0;

  if (tcsetattr(serial_fd_, TCSANOW, &settings) != 0) {
    close_serial_port();
    return false;
  }
  tcflush(serial_fd_, TCIOFLUSH);
  receive_buffer_.clear();
  return true;
}

void MiniFarmbotSystem::close_serial_port()
{
  if (serial_fd_ >= 0) {
    close(serial_fd_);
    serial_fd_ = -1;
  }
}

bool MiniFarmbotSystem::send_line(const std::string & line)
{
  if (serial_fd_ < 0) {
    return false;
  }

  const std::string message = line + "\n";
  std::size_t sent = 0;
  while (sent < message.size()) {
    const ssize_t result = ::write(serial_fd_, message.data() + sent, message.size() - sent);
    if (result > 0) {
      sent += static_cast<std::size_t>(result);
    } else if (result < 0 && (errno == EAGAIN || errno == EINTR)) {
      continue;
    } else {
      return false;
    }
  }
  return true;
}

void MiniFarmbotSystem::process_serial_input()
{
  if (serial_fd_ < 0) {
    return;
  }

  char buffer[256];
  const ssize_t received = ::read(serial_fd_, buffer, sizeof(buffer));
  if (received <= 0) {
    return;
  }
  receive_buffer_.append(buffer, static_cast<std::size_t>(received));

  std::size_t newline = receive_buffer_.find('\n');
  while (newline != std::string::npos) {
    std::string line = receive_buffer_.substr(0, newline);
    if (!line.empty() && line.back() == '\r') {
      line.pop_back();
    }
    receive_buffer_.erase(0, newline + 1);
    process_serial_line(line);
    newline = receive_buffer_.find('\n');
  }
}

void MiniFarmbotSystem::process_serial_line(const std::string & line)
{
  std::istringstream message(line);
  std::string type;
  message >> type;
  if (type != "STATE") {
    return;
  }

  long steps[3]{};
  std::string state;
  if (!(message >> steps[0] >> steps[1] >> steps[2] >> state)) {
    return;
  }
  for (std::size_t index = 0; index < 3 && index < positions_.size(); ++index) {
    positions_[index] = steps_to_meters(steps[index], index);
  }
}

long MiniFarmbotSystem::meters_to_steps(double position, std::size_t axis) const
{
  return static_cast<long>(position * steps_per_meter_[axis]);
}

double MiniFarmbotSystem::steps_to_meters(long steps, std::size_t axis) const
{
  return static_cast<double>(steps) / steps_per_meter_[axis];
}

}  // namespace mini_farmbot_hardware

PLUGINLIB_EXPORT_CLASS(
  mini_farmbot_hardware::MiniFarmbotSystem, hardware_interface::SystemInterface)