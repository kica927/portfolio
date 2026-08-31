#include "so101_hardware/sts3215_system.hpp"

#include <cmath>
#include <cstring>
#include <fcntl.h>
#include <numeric>
#include <termios.h>
#include <unistd.h>

#include "hardware_interface/types/hardware_interface_type_values.hpp"
#include "rclcpp/rclcpp.hpp"

namespace so101_hardware
{
static const rclcpp::Logger LOG = rclcpp::get_logger("STS3215System");

// Feetech registers / instructions
static constexpr uint8_t INST_PING = 0x01, INST_READ = 0x02, INST_WRITE = 0x03;
static constexpr uint8_t ADDR_TORQUE_ENABLE = 40, ADDR_GOAL_POSITION = 42,
                         ADDR_PRESENT_POSITION = 56;

// ---------------- FeetechBus ----------------
bool FeetechBus::open_port(const std::string & port, int baud)
{
  fd_ = ::open(port.c_str(), O_RDWR | O_NOCTTY | O_NDELAY);
  if (fd_ < 0) { RCLCPP_ERROR(LOG, "포트 열기 실패: %s", port.c_str()); return false; }
  fcntl(fd_, F_SETFL, 0);
  termios tty{};
  if (tcgetattr(fd_, &tty) != 0) { return false; }
  cfmakeraw(&tty);
  // 1,000,000 baud (STS3215 기본). B1000000 는 리눅스에서 지원.
  speed_t sp = (baud == 1000000) ? B1000000 : B115200;
  cfsetispeed(&tty, sp); cfsetospeed(&tty, sp);
  tty.c_cflag |= (CLOCAL | CREAD);
  tty.c_cflag &= ~(PARENB | CSTOPB | CRTSCTS);
  tty.c_cflag = (tty.c_cflag & ~CSIZE) | CS8;
  tty.c_cc[VMIN] = 0; tty.c_cc[VTIME] = 2;   // 0.2s 타임아웃
  return tcsetattr(fd_, TCSANOW, &tty) == 0;
}

void FeetechBus::close_port() { if (fd_ >= 0) { ::close(fd_); fd_ = -1; } }

bool FeetechBus::transact(uint8_t id, uint8_t inst, const std::vector<uint8_t> & params,
                          std::vector<uint8_t> & response, size_t expect_params)
{
  if (fd_ < 0) { return false; }
  uint8_t len = static_cast<uint8_t>(params.size() + 2);
  std::vector<uint8_t> pkt{0xFF, 0xFF, id, len, inst};
  pkt.insert(pkt.end(), params.begin(), params.end());
  int sum = std::accumulate(pkt.begin() + 2, pkt.end(), 0);
  pkt.push_back(static_cast<uint8_t>(~sum & 0xFF));

  tcflush(fd_, TCIFLUSH);
  if (::write(fd_, pkt.data(), pkt.size()) != static_cast<ssize_t>(pkt.size())) { return false; }

  // 응답: [0xFF][0xFF][ID][Len][Error][Params...][Checksum], 총 4+Len
  uint8_t hdr[4]; size_t got = 0;
  while (got < 4) {
    ssize_t n = ::read(fd_, hdr + got, 4 - got);
    if (n <= 0) { return false; }
    got += n;
  }
  if (hdr[0] != 0xFF || hdr[1] != 0xFF) { return false; }
  size_t remaining = hdr[3];                    // Len 바이트(Error+params+checksum)
  response.assign(remaining, 0); got = 0;
  while (got < remaining) {
    ssize_t n = ::read(fd_, response.data() + got, remaining - got);
    if (n <= 0) { return false; }
    got += n;
  }
  // response = [Error][params...][checksum] → 데이터는 [1 .. 1+expect_params)
  if (response.size() < expect_params + 2) { return false; }
  response.erase(response.begin());             // drop Error
  response.pop_back();                          // drop checksum
  return true;
}

bool FeetechBus::ping(uint8_t id)
{
  std::vector<uint8_t> r; return transact(id, INST_PING, {}, r, 0);
}
bool FeetechBus::read_u16(uint8_t id, uint8_t addr, uint16_t & out)
{
  std::vector<uint8_t> r;
  if (!transact(id, INST_READ, {addr, 2}, r, 2) || r.size() < 2) { return false; }
  out = static_cast<uint16_t>(r[0] | (r[1] << 8));   // little-endian
  return true;
}
bool FeetechBus::write_u16(uint8_t id, uint8_t addr, uint16_t v)
{
  std::vector<uint8_t> r;
  return transact(id, INST_WRITE, {addr, static_cast<uint8_t>(v & 0xFF),
                                   static_cast<uint8_t>((v >> 8) & 0xFF)}, r, 0);
}
bool FeetechBus::write_u8(uint8_t id, uint8_t addr, uint8_t v)
{
  std::vector<uint8_t> r; return transact(id, INST_WRITE, {addr, v}, r, 0);
}

// ---------------- STS3215System ----------------
hardware_interface::CallbackReturn STS3215System::on_init(
  const hardware_interface::HardwareInfo & info)
{
  if (SystemInterface::on_init(info) != hardware_interface::CallbackReturn::SUCCESS) {
    return hardware_interface::CallbackReturn::ERROR;
  }
  port_ = info_.hardware_parameters.count("port") ? info_.hardware_parameters.at("port")
                                                  : std::string("/dev/ttyACM0");
  if (info_.hardware_parameters.count("baud")) {
    baud_ = std::stoi(info_.hardware_parameters.at("baud"));
  }
  const size_t n = info_.joints.size();
  hw_positions_.assign(n, std::numeric_limits<double>::quiet_NaN());
  hw_commands_.assign(n, std::numeric_limits<double>::quiet_NaN());
  servo_ids_.resize(n);
  for (size_t i = 0; i < n; ++i) {
    const auto & jp = info_.joints[i].parameters;
    servo_ids_[i] = jp.count("id") ? static_cast<uint8_t>(std::stoi(jp.at("id")))
                                   : static_cast<uint8_t>(i + 1);
  }
  return hardware_interface::CallbackReturn::SUCCESS;
}

hardware_interface::CallbackReturn STS3215System::on_configure(
  const rclcpp_lifecycle::State &)
{
  if (!bus_.open_port(port_, baud_)) { return hardware_interface::CallbackReturn::ERROR; }
  RCLCPP_INFO(LOG, "STS3215 버스 열림: %s @ %d", port_.c_str(), baud_);
  return hardware_interface::CallbackReturn::SUCCESS;
}

hardware_interface::CallbackReturn STS3215System::on_activate(
  const rclcpp_lifecycle::State &)
{
  for (size_t i = 0; i < servo_ids_.size(); ++i) {
    bus_.write_u8(servo_ids_[i], ADDR_TORQUE_ENABLE, 1);
    uint16_t pos = kCenter;
    if (bus_.read_u16(servo_ids_[i], ADDR_PRESENT_POSITION, pos)) {
      hw_positions_[i] = (static_cast<int>(pos) - kCenter) * (2.0 * M_PI / kCountsPerRev);
    }
    hw_commands_[i] = hw_positions_[i];   // 정지 상태로 시작 (현재값 유지)
  }
  RCLCPP_INFO(LOG, "토크 ON · 초기 위치 읽음");
  return hardware_interface::CallbackReturn::SUCCESS;
}

hardware_interface::CallbackReturn STS3215System::on_deactivate(
  const rclcpp_lifecycle::State &)
{
  for (auto id : servo_ids_) { bus_.write_u8(id, ADDR_TORQUE_ENABLE, 0); }
  bus_.close_port();
  return hardware_interface::CallbackReturn::SUCCESS;
}

std::vector<hardware_interface::StateInterface> STS3215System::export_state_interfaces()
{
  std::vector<hardware_interface::StateInterface> ifaces;
  for (size_t i = 0; i < info_.joints.size(); ++i) {
    ifaces.emplace_back(info_.joints[i].name, hardware_interface::HW_IF_POSITION,
                        &hw_positions_[i]);
  }
  return ifaces;
}

std::vector<hardware_interface::CommandInterface> STS3215System::export_command_interfaces()
{
  std::vector<hardware_interface::CommandInterface> ifaces;
  for (size_t i = 0; i < info_.joints.size(); ++i) {
    ifaces.emplace_back(info_.joints[i].name, hardware_interface::HW_IF_POSITION,
                        &hw_commands_[i]);
  }
  return ifaces;
}

hardware_interface::return_type STS3215System::read(
  const rclcpp::Time &, const rclcpp::Duration &)
{
  for (size_t i = 0; i < servo_ids_.size(); ++i) {
    uint16_t pos;
    if (bus_.read_u16(servo_ids_[i], ADDR_PRESENT_POSITION, pos)) {
      hw_positions_[i] = (static_cast<int>(pos) - kCenter) * (2.0 * M_PI / kCountsPerRev);
    }
  }
  return hardware_interface::return_type::OK;
}

hardware_interface::return_type STS3215System::write(
  const rclcpp::Time &, const rclcpp::Duration &)
{
  for (size_t i = 0; i < servo_ids_.size(); ++i) {
    if (std::isnan(hw_commands_[i])) { continue; }
    long counts = std::lround(hw_commands_[i] * (kCountsPerRev / (2.0 * M_PI))) + kCenter;
    counts = std::max(0L, std::min(4095L, counts));
    bus_.write_u16(servo_ids_[i], ADDR_GOAL_POSITION, static_cast<uint16_t>(counts));
  }
  return hardware_interface::return_type::OK;
}

}  // namespace so101_hardware

#include "pluginlib/class_list_macros.hpp"
PLUGINLIB_EXPORT_CLASS(so101_hardware::STS3215System, hardware_interface::SystemInterface)
