#include <Arduino.h>
#include <AccelStepper.h>
#include <stdlib.h>
#include <string.h>

#include "command_protocol.hpp"
#include "pin_config.hpp"

namespace
{
enum class AxisState : uint8_t
{
  IDLE,
  HOMING_SEEK,
  HOMING_BACKOFF,
  ERROR
};

struct Axis
{
  const char * name;
  AccelStepper * motor;
  uint8_t limit_pin;
  int homing_direction;
  AxisState state;
  bool homed;
};

AccelStepper x_motor(
  AccelStepper::DRIVER, mini_farmbot_pins::X_STEP, mini_farmbot_pins::X_DIRECTION);
AccelStepper y_motor(
  AccelStepper::DRIVER, mini_farmbot_pins::Y_STEP, mini_farmbot_pins::Y_DIRECTION);
AccelStepper z_motor(
  AccelStepper::DRIVER, mini_farmbot_pins::Z_STEP, mini_farmbot_pins::Z_DIRECTION);

Axis axes[] = {
  {"X", &x_motor, mini_farmbot_pins::X_LIMIT, -1, AxisState::IDLE, false},
  {"Y", &y_motor, mini_farmbot_pins::Y_LIMIT, -1, AxisState::IDLE, false},
  {"Z", &z_motor, mini_farmbot_pins::Z_LIMIT, -1, AxisState::IDLE, false},
};
constexpr uint8_t AXIS_COUNT = sizeof(axes) / sizeof(axes[0]);

char command_line[mini_farmbot_protocol::MAX_LINE_LENGTH];
unsigned int command_length = 0;
unsigned long last_status_time = 0;
long active_command_id = 0;
bool move_active = false;
bool homing_active = false;
bool fault_active = false;
bool was_busy = false;

bool limit_is_active(const Axis & axis)
{
  const int value = digitalRead(axis.limit_pin);
  return mini_farmbot_pins::LIMIT_SWITCH_ACTIVE_LOW ? value == LOW : value == HIGH;
}

bool any_axis_busy()
{
  for (uint8_t index = 0; index < AXIS_COUNT; ++index) {
    if (axes[index].state != AxisState::IDLE || axes[index].motor->distanceToGo() != 0) {
      return true;
    }
  }
  return false;
}

bool all_axes_homed()
{
  for (uint8_t index = 0; index < AXIS_COUNT; ++index) {
    if (!axes[index].homed) {
      return false;
    }
  }
  return true;
}

bool controller_busy()
{
  return homing_active || any_axis_busy();
}

const char * current_state_name()
{
  if (fault_active) {
    return "ERROR";
  }
  if (homing_active) {
    return "HOMING";
  }
  return any_axis_busy() ? "MOVING" : "IDLE";
}

void print_positions(const char * state)
{
  Serial.print("STATE ");
  Serial.print(x_motor.currentPosition());
  Serial.print(' ');
  Serial.print(y_motor.currentPosition());
  Serial.print(' ');
  Serial.print(z_motor.currentPosition());
  Serial.print(' ');
  Serial.println(state);
}

void stop_all_axes()
{
  for (uint8_t index = 0; index < AXIS_COUNT; ++index) {
    axes[index].motor->stop();
    axes[index].state = AxisState::IDLE;
  }
  move_active = false;
  homing_active = false;
}

void begin_homing(Axis & axis)
{
  axis.homed = false;
  axis.state = AxisState::HOMING_SEEK;
  axis.motor->setMaxSpeed(mini_farmbot_protocol::HOMING_SPEED_STEPS_PER_SECOND);
  axis.motor->setAcceleration(
    mini_farmbot_protocol::DEFAULT_ACCELERATION_STEPS_PER_SECOND_SQUARED);

  if (limit_is_active(axis)) {
    axis.motor->setCurrentPosition(0);
    axis.motor->moveTo(-axis.homing_direction * mini_farmbot_protocol::HOMING_BACKOFF_STEPS);
    axis.state = AxisState::HOMING_BACKOFF;
  } else {
    axis.motor->moveTo(axis.motor->currentPosition() +
      axis.homing_direction * mini_farmbot_protocol::HOMING_TRAVEL_STEPS);
  }
}

void handle_home(const char * axis_name)
{
  if (any_axis_busy()) {
    Serial.println("ERROR BUSY");
    return;
  }

  bool found_axis = false;
  for (uint8_t index = 0; index < AXIS_COUNT; ++index) {
    if (strcmp(axis_name, "ALL") == 0 || strcmp(axis_name, axes[index].name) == 0) {
      begin_homing(axes[index]);
      found_axis = true;
    }
  }

  if (!found_axis) {
    Serial.println("ERROR INVALID_AXIS");
    return;
  }

  homing_active = true;
  fault_active = false;
  Serial.println("ACK HOME");
}

void handle_move(char * first_token)
{
  if (homing_active || fault_active) {
    Serial.println("ERROR BUSY");
    return;
  }
  if (mini_farmbot_pins::REQUIRE_HOMING_BEFORE_MOVE && !all_axes_homed()) {
    Serial.println("ERROR NOT_HOMED");
    return;
  }

  long targets[AXIS_COUNT];
  char * token = first_token;
  for (uint8_t index = 0; index < AXIS_COUNT; ++index) {
    if (token == nullptr) {
      Serial.println("ERROR INVALID_MOVE");
      return;
    }
    targets[index] = atol(token);
    token = strtok(nullptr, " ");
  }

  token = strtok(nullptr, " ");
  if (token == nullptr) {
    Serial.println("ERROR INVALID_MOVE");
    return;
  }
  const float speed = atof(token);
  if (speed <= 0.0F) {
    Serial.println("ERROR INVALID_SPEED");
    return;
  }

  token = strtok(nullptr, " ");
  active_command_id = token == nullptr ? 0 : atol(token);

  for (uint8_t index = 0; index < AXIS_COUNT; ++index) {
    axes[index].motor->setMaxSpeed(speed);
    axes[index].motor->setAcceleration(
      mini_farmbot_protocol::DEFAULT_ACCELERATION_STEPS_PER_SECOND_SQUARED);
    axes[index].motor->moveTo(targets[index]);
  }

  move_active = true;
  Serial.print("ACK MOVE ");
  Serial.println(active_command_id);
}

void handle_command(char * command)
{
  char * operation = strtok(command, " ");
  if (operation == nullptr) {
    return;
  }

  if (strcmp(operation, "PING") == 0) {
    Serial.println("PONG");
  } else if (strcmp(operation, "STATUS") == 0) {
    print_positions(current_state_name());
  } else if (strcmp(operation, "STOP") == 0) {
    stop_all_axes();
    Serial.println("ACK STOP");
  } else if (strcmp(operation, "HOME") == 0) {
    const char * axis_name = strtok(nullptr, " ");
    handle_home(axis_name == nullptr ? "ALL" : axis_name);
  } else if (strcmp(operation, "MOVE") == 0) {
    handle_move(strtok(nullptr, " "));
  } else {
    Serial.println("ERROR UNKNOWN_COMMAND");
  }
}

void read_serial_commands()
{
  while (Serial.available() > 0) {
    const char character = static_cast<char>(Serial.read());
    if (character == '\n' || character == '\r') {
      if (command_length > 0) {
        command_line[command_length] = '\0';
        handle_command(command_line);
        command_length = 0;
      }
      continue;
    }

    if (command_length + 1 < mini_farmbot_protocol::MAX_LINE_LENGTH) {
      command_line[command_length++] = character;
    } else {
      command_length = 0;
      Serial.println("ERROR COMMAND_TOO_LONG");
    }
  }
}

void run_homing()
{
  for (uint8_t index = 0; index < AXIS_COUNT; ++index) {
    Axis & axis = axes[index];
    if (axis.state == AxisState::HOMING_SEEK) {
      if (limit_is_active(axis)) {
        axis.motor->stop();
        axis.motor->setCurrentPosition(0);
        axis.motor->moveTo(-axis.homing_direction * mini_farmbot_protocol::HOMING_BACKOFF_STEPS);
        axis.state = AxisState::HOMING_BACKOFF;
      } else if (axis.motor->distanceToGo() == 0) {
        axis.state = AxisState::ERROR;
        fault_active = true;
        Serial.print("ERROR HOMING_TIMEOUT_");
        Serial.println(axis.name);
      }
    } else if (axis.state == AxisState::HOMING_BACKOFF && axis.motor->distanceToGo() == 0) {
      axis.motor->setCurrentPosition(0);
      axis.homed = true;
      axis.state = AxisState::IDLE;
    }
  }

  if (homing_active && !any_axis_busy()) {
    homing_active = false;
    if (!fault_active) {
      Serial.println("DONE HOME");
    }
  }
}

void run_motors()
{
  for (uint8_t index = 0; index < AXIS_COUNT; ++index) {
    Axis & axis = axes[index];
    if (axis.state == AxisState::IDLE && !homing_active && limit_is_active(axis) &&
      axis.motor->distanceToGo() < 0)
    {
      axis.motor->stop();
      axis.state = AxisState::ERROR;
      fault_active = true;
      Serial.print("ERROR LIMIT_");
      Serial.println(axis.name);
    }
    axis.motor->run();
  }

  if (move_active && !any_axis_busy()) {
    move_active = false;
    Serial.print("DONE MOVE ");
    Serial.println(active_command_id);
  }
}

// Meldet die Position periodisch, solange sich etwas bewegt (Fahrt, Homing, Abbremsen nach STOP),
// und genau einmal beim Stillstand. Ohne diese letzte Meldung bliebe in ROS die Position der
// letzten periodischen Meldung stehen, also bis zu STATUS_INTERVAL_MS vor dem tatsaechlichen Ziel.
void publish_status()
{
  const bool busy = controller_busy();
  if (busy) {
    const unsigned long now = millis();
    if (now - last_status_time >= mini_farmbot_protocol::STATUS_INTERVAL_MS) {
      last_status_time = now;
      print_positions(current_state_name());
    }
  } else if (was_busy) {
    print_positions(current_state_name());
  }
  was_busy = busy;
}
}  // namespace

void setup()
{
  pinMode(mini_farmbot_pins::DRIVER_ENABLE, OUTPUT);
  digitalWrite(
    mini_farmbot_pins::DRIVER_ENABLE,
    mini_farmbot_pins::DRIVER_ENABLE_ACTIVE_LOW ? LOW : HIGH);

  for (uint8_t index = 0; index < AXIS_COUNT; ++index) {
    pinMode(axes[index].limit_pin, INPUT_PULLUP);
    axes[index].motor->setAcceleration(
      mini_farmbot_protocol::DEFAULT_ACCELERATION_STEPS_PER_SECOND_SQUARED);
  }

  Serial.begin(mini_farmbot_protocol::SERIAL_BAUD_RATE);
  Serial.println("READY 1");
}

void loop()
{
  read_serial_commands();
  run_homing();
  run_motors();
  publish_status();
}
