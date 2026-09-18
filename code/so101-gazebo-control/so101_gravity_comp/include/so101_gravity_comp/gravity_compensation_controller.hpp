#ifndef SO101_GRAVITY_COMP__GRAVITY_COMPENSATION_CONTROLLER_HPP_
#define SO101_GRAVITY_COMP__GRAVITY_COMPENSATION_CONTROLLER_HPP_

#include <mutex>
#include <string>
#include <vector>

#include <Eigen/Core>
#include <pinocchio/multibody/data.hpp>
#include <pinocchio/multibody/model.hpp>

#include "control_msgs/msg/joint_trajectory_controller_state.hpp"
#include "controller_interface/chainable_controller_interface.hpp"
#include "hardware_interface/handle.hpp"
#include "rclcpp/subscription.hpp"

namespace so101_gravity_comp
{

// 상위 컨트롤러(JTC)가 보낸 토크 reference 에 동역학 피드포워드를 더해 관절 effort 로 쓴다.
//   feedforward = gravity : g(q)
//   feedforward = nle     : C(q,q')q' + g(q)
//   feedforward = full    : M(q)q''_d + C(q,q')q' + g(q)  (q''_d 는 JTC 상태 토픽에서 받는다 — 실시간 경로 아님)
// 체인이 없으면 reference 는 0 이므로 피드포워드만 나간다.
class GravityCompensationController : public controller_interface::ChainableControllerInterface
{
public:
  controller_interface::CallbackReturn on_init() override;
  controller_interface::InterfaceConfiguration command_interface_configuration() const override;
  controller_interface::InterfaceConfiguration state_interface_configuration() const override;
  controller_interface::CallbackReturn on_configure(const rclcpp_lifecycle::State & previous_state) override;
  controller_interface::CallbackReturn on_activate(const rclcpp_lifecycle::State & previous_state) override;
  controller_interface::CallbackReturn on_deactivate(const rclcpp_lifecycle::State & previous_state) override;

  controller_interface::return_type update_reference_from_subscribers(
    const rclcpp::Time & time, const rclcpp::Duration & period) override;
  controller_interface::return_type update_and_write_commands(
    const rclcpp::Time & time, const rclcpp::Duration & period) override;

protected:
  std::vector<hardware_interface::CommandInterface> on_export_reference_interfaces() override;
  bool on_set_chained_mode(bool chained_mode) override;

private:
  enum class Feedforward { kGravity, kNonlinear, kFull };

  void on_reference_state(const control_msgs::msg::JointTrajectoryControllerState & msg);

  std::vector<std::string> joints_;
  std::vector<std::string> extra_state_joints_;
  double scale_{1.0};
  Feedforward feedforward_{Feedforward::kGravity};

  pinocchio::Model model_;
  pinocchio::Data data_;
  Eigen::VectorXd q_;
  Eigen::VectorXd v_;
  Eigen::VectorXd a_;
  std::vector<int> joint_q_index_;
  std::vector<int> extra_q_index_;

  rclcpp::Subscription<control_msgs::msg::JointTrajectoryControllerState>::SharedPtr reference_sub_;
  std::mutex reference_mutex_;
  std::vector<double> reference_accel_;
};

}  // namespace so101_gravity_comp

#endif  // SO101_GRAVITY_COMP__GRAVITY_COMPENSATION_CONTROLLER_HPP_
