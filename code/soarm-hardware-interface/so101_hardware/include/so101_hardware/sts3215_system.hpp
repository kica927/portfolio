// STS3215 ros2_control SystemInterface — SO-ARM101 실물 팔.
// mock_components/GenericSystem 을 대체해 MoveIt 궤적을 실제 Feetech 서보로 낸다.
#ifndef SO101_HARDWARE__STS3215_SYSTEM_HPP_
#define SO101_HARDWARE__STS3215_SYSTEM_HPP_

#include <string>
#include <vector>
#include "hardware_interface/system_interface.hpp"
#include "hardware_interface/types/hardware_interface_return_values.hpp"
#include "rclcpp/macros.hpp"

namespace so101_hardware
{

// 최소 Feetech STS3215 half-duplex UART 드라이버 (termios).
// 프로토콜: [0xFF][0xFF][ID][Len][Inst][Params...][~sum(from ID)]
class FeetechBus
{
public:
  bool open_port(const std::string & port, int baud);   // baud=1000000
  void close_port();
  bool ping(uint8_t id);
  bool read_u16(uint8_t id, uint8_t addr, uint16_t & out);   // PRESENT_POSITION=56
  bool write_u16(uint8_t id, uint8_t addr, uint16_t value);  // GOAL_POSITION=42
  bool write_u8(uint8_t id, uint8_t addr, uint8_t value);    // TORQUE_ENABLE=40
private:
  bool transact(uint8_t id, uint8_t inst, const std::vector<uint8_t> & params,
                std::vector<uint8_t> & response, size_t expect_params);
  int fd_{-1};
};

class STS3215System : public hardware_interface::SystemInterface
{
public:
  RCLCPP_SHARED_PTR_DEFINITIONS(STS3215System)

  hardware_interface::CallbackReturn on_init(
    const hardware_interface::HardwareInfo & info) override;
  hardware_interface::CallbackReturn on_configure(
    const rclcpp_lifecycle::State & previous_state) override;
  hardware_interface::CallbackReturn on_activate(
    const rclcpp_lifecycle::State & previous_state) override;
  hardware_interface::CallbackReturn on_deactivate(
    const rclcpp_lifecycle::State & previous_state) override;

  std::vector<hardware_interface::StateInterface> export_state_interfaces() override;
  std::vector<hardware_interface::CommandInterface> export_command_interfaces() override;

  hardware_interface::return_type read(
    const rclcpp::Time & time, const rclcpp::Duration & period) override;
  hardware_interface::return_type write(
    const rclcpp::Time & time, const rclcpp::Duration & period) override;

private:
  static constexpr int kCenter = 2048;
  static constexpr double kCountsPerRev = 4096.0;   // rad = (pos-2048)*2π/4096

  FeetechBus bus_;
  std::string port_;
  int baud_{1000000};
  std::vector<uint8_t> servo_ids_;          // hardware_parameter "id" per joint
  std::vector<double> hw_positions_;        // state  [rad]
  std::vector<double> hw_commands_;         // command[rad]
};

}  // namespace so101_hardware
#endif  // SO101_HARDWARE__STS3215_SYSTEM_HPP_
