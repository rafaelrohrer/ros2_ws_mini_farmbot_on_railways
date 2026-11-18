#ifndef MINI_FARMBOT_COMMAND_PROTOCOL_HPP
#define MINI_FARMBOT_COMMAND_PROTOCOL_HPP

namespace mini_farmbot_protocol
{

constexpr long SERIAL_BAUD_RATE = 115200;
constexpr unsigned int MAX_LINE_LENGTH = 128;
constexpr unsigned long STATUS_INTERVAL_MS = 250;
constexpr long HOMING_TRAVEL_STEPS = 200000L;
constexpr long HOMING_BACKOFF_STEPS = 400L;
constexpr float HOMING_SPEED_STEPS_PER_SECOND = 300.0F;
constexpr float DEFAULT_ACCELERATION_STEPS_PER_SECOND_SQUARED = 800.0F;

}  // namespace mini_farmbot_protocol

#endif