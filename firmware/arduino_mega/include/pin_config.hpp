#ifndef MINI_FARMBOT_PIN_CONFIG_HPP
#define MINI_FARMBOT_PIN_CONFIG_HPP

#include <Arduino.h>

namespace mini_farmbot_pins
{

constexpr uint8_t X_STEP = 2;
constexpr uint8_t X_DIRECTION = 5;
constexpr uint8_t X_LIMIT = 9;

constexpr uint8_t Y_STEP = 3;
constexpr uint8_t Y_DIRECTION = 6;
constexpr uint8_t Y_LIMIT = 10;

constexpr uint8_t Z_STEP = 4;
constexpr uint8_t Z_DIRECTION = 7;
constexpr uint8_t Z_LIMIT = 11;

constexpr uint8_t DRIVER_ENABLE = 8;
constexpr bool LIMIT_SWITCH_ACTIVE_LOW = true;
constexpr bool DRIVER_ENABLE_ACTIVE_LOW = true;
constexpr bool REQUIRE_HOMING_BEFORE_MOVE = false;

}  // namespace mini_farmbot_pins

#endif