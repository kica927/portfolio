#include "so101_gravity_comp/gravity_compensation_controller.hpp"

#include <algorithm>
#include <cmath>

#include <pinocchio/algorithm/rnea.hpp>
#include <pinocchio/parsers/urdf.hpp>

#include "pluginlib/class_list_macros.hpp"

namespace so101_gravity_comp
{

controller_interface::CallbackReturn GravityCompensationController::on_init()
{
  auto_declare<std::vector<std::string>>("joints", {});
  auto_declare<std::vector<std::string>>("extra_state_joints", {});
  auto_declare<double>("scale", 1.0);
  auto_declare<std::string>("feedforward", "gravity");
  auto_declare<std::string>("reference_state_topic", "/arm_controller/controller_state");
  return controller_interface::CallbackReturn::SUCCESS;
}

controller_interface::InterfaceConfiguration
GravityCompensationController::command_interface_configuration() const
{
  controller_interface::InterfaceConfiguration config;
  config.type = controller_interface::interface_configuration_type::INDIVIDUAL;
  for (const auto & joint : joints_) {
    config.names.push_back(joint + "/effort");
  }
  return config;
}

controller_interface::InterfaceConfiguration
GravityCompensationController::state_interface_configuration() const
{
  // 순서: 팔 관절 position, 팔 관절 velocity, 추가 관절 position
  controller_interface::InterfaceConfiguration config;
  config.type = controller_interface::interface_configuration_type::INDIVIDUAL;
  for (const auto & joint : joints_) {
    config.names.push_back(joint + "/position");
  }
  for (const auto & joint : joints_) {
    config.names.push_back(joint + "/velocity");
  }
  for (const auto & joint : extra_state_joints_) {
    config.names.push_back(joint + "/position");
  }
  return config;
}

controller_interface::CallbackReturn GravityCompensationController::on_configure(
  const rclcpp_lifecycle::State &)
{
  joints_ = get_node()->get_parameter("joints").as_string_array();
  extra_state_joints_ = get_node()->get_parameter("extra_state_joints").as_string_array();
  scale_ = get_node()->get_parameter("scale").as_double();
  const std::string mode = get_node()->get_parameter("feedforward").as_string();
  if (mode == "gravity") {
    feedforward_ = Feedforward::kGravity;
  } else if (mode == "nle") {
    feedforward_ = Feedforward::kNonlinear;
  } else if (mode == "full") {
    feedforward_ = Feedforward::kFull;
  } else {
    RCLCPP_ERROR(get_node()->get_logger(), "feedforward 는 gravity | nle | full 중 하나여야 합니다: '%s'", mode.c_str());
    return controller_interface::CallbackReturn::ERROR;
  }
  if (joints_.empty()) {
    RCLCPP_ERROR(get_node()->get_logger(), "'joints' 파라미터가 비어 있습니다");
    return controller_interface::CallbackReturn::ERROR;
  }

  const std::string & urdf = get_robot_description();
  if (urdf.empty()) {
    RCLCPP_ERROR(get_node()->get_logger(), "robot_description 이 비어 있습니다");
    return controller_interface::CallbackReturn::ERROR;
  }
  try {
    pinocchio::urdf::buildModelFromXML(urdf, model_);
  } catch (const std::exception & e) {
    RCLCPP_ERROR(get_node()->get_logger(), "Pinocchio 모델 생성 실패: %s", e.what());
    return controller_interface::CallbackReturn::ERROR;
  }
  data_ = pinocchio::Data(model_);
  q_ = Eigen::VectorXd::Zero(model_.nq);
  v_ = Eigen::VectorXd::Zero(model_.nv);
  a_ = Eigen::VectorXd::Zero(model_.nv);

  auto index_of = [this](const std::string & name) -> int {
      if (!model_.existJointName(name)) {
        return -1;
      }
      return model_.joints[model_.getJointId(name)].idx_q();
    };
  joint_q_index_.clear();
  extra_q_index_.clear();
  for (const auto & joint : joints_) {
    const int idx = index_of(joint);
    if (idx < 0) {
      RCLCPP_ERROR(get_node()->get_logger(), "모델에 관절 '%s' 가 없습니다", joint.c_str());
      return controller_interface::CallbackReturn::ERROR;
    }
    joint_q_index_.push_back(idx);
  }
  for (const auto & joint : extra_state_joints_) {
    const int idx = index_of(joint);
    if (idx < 0) {
      RCLCPP_ERROR(get_node()->get_logger(), "모델에 관절 '%s' 가 없습니다", joint.c_str());
      return controller_interface::CallbackReturn::ERROR;
    }
    extra_q_index_.push_back(idx);
  }

  reference_interfaces_.assign(joints_.size(), 0.0);
  reference_accel_.assign(joints_.size(), 0.0);
  reference_sub_.reset();
  if (feedforward_ == Feedforward::kFull) {
    const std::string topic = get_node()->get_parameter("reference_state_topic").as_string();
    reference_sub_ = get_node()->create_subscription<control_msgs::msg::JointTrajectoryControllerState>(
      topic, rclcpp::SystemDefaultsQoS(),
      [this](const control_msgs::msg::JointTrajectoryControllerState & msg) {on_reference_state(msg);});
  }
  RCLCPP_INFO(get_node()->get_logger(), "동역학 피드포워드 준비: 관절 %zu 개, 모델 nq=%d, 모드=%s, scale=%.3f",
    joints_.size(), model_.nq, mode.c_str(), scale_);
  return controller_interface::CallbackReturn::SUCCESS;
}

void GravityCompensationController::on_reference_state(
  const control_msgs::msg::JointTrajectoryControllerState & msg)
{
  const auto & accel = msg.reference.accelerations;
  if (accel.size() != msg.joint_names.size()) {
    return;
  }
  std::vector<double> ordered(joints_.size(), 0.0);
  for (size_t i = 0; i < joints_.size(); ++i) {
    const auto it = std::find(msg.joint_names.begin(), msg.joint_names.end(), joints_[i]);
    if (it == msg.joint_names.end()) {
      return;
    }
    ordered[i] = accel[static_cast<size_t>(it - msg.joint_names.begin())];
  }
  std::lock_guard<std::mutex> lock(reference_mutex_);
  reference_accel_ = ordered;
}

std::vector<hardware_interface::CommandInterface>
GravityCompensationController::on_export_reference_interfaces()
{
  reference_interfaces_.assign(joints_.size(), 0.0);
  std::vector<hardware_interface::CommandInterface> interfaces;
  interfaces.reserve(joints_.size());
  for (size_t i = 0; i < joints_.size(); ++i) {
    interfaces.emplace_back(get_node()->get_name(), joints_[i] + "/effort", &reference_interfaces_[i]);
  }
  return interfaces;
}

bool GravityCompensationController::on_set_chained_mode(bool)
{
  return true;
}

controller_interface::CallbackReturn GravityCompensationController::on_activate(
  const rclcpp_lifecycle::State &)
{
  std::fill(reference_interfaces_.begin(), reference_interfaces_.end(), 0.0);
  std::lock_guard<std::mutex> lock(reference_mutex_);
  std::fill(reference_accel_.begin(), reference_accel_.end(), 0.0);
  return controller_interface::CallbackReturn::SUCCESS;
}

controller_interface::CallbackReturn GravityCompensationController::on_deactivate(
  const rclcpp_lifecycle::State &)
{
  for (auto & command : command_interfaces_) {
    (void)command.set_value(0.0);
  }
  return controller_interface::CallbackReturn::SUCCESS;
}

controller_interface::return_type GravityCompensationController::update_reference_from_subscribers(
  const rclcpp::Time &, const rclcpp::Duration &)
{
  return controller_interface::return_type::OK;
}

controller_interface::return_type GravityCompensationController::update_and_write_commands(
  const rclcpp::Time &, const rclcpp::Duration &)
{
  const size_t n = joints_.size();
  for (size_t i = 0; i < n; ++i) {
    if (const auto value = state_interfaces_[i].get_optional()) {
      q_[joint_q_index_[i]] = *value;
    }
    if (const auto value = state_interfaces_[n + i].get_optional()) {
      v_[joint_q_index_[i]] = *value;
    }
  }
  for (size_t i = 0; i < extra_q_index_.size(); ++i) {
    if (const auto value = state_interfaces_[2 * n + i].get_optional()) {
      q_[extra_q_index_[i]] = *value;
    }
  }

  Eigen::VectorXd tau;
  if (feedforward_ == Feedforward::kGravity) {
    tau = pinocchio::computeGeneralizedGravity(model_, data_, q_);
  } else {
    a_.setZero();
    if (feedforward_ == Feedforward::kFull) {
      std::unique_lock<std::mutex> lock(reference_mutex_, std::try_to_lock);
      if (lock.owns_lock()) {
        for (size_t i = 0; i < n; ++i) {
          a_[joint_q_index_[i]] = reference_accel_[i];
        }
      }
    }
    tau = pinocchio::rnea(model_, data_, q_, v_, a_);
  }

  for (size_t i = 0; i < n; ++i) {
    const double reference = std::isfinite(reference_interfaces_[i]) ? reference_interfaces_[i] : 0.0;
    (void)command_interfaces_[i].set_value(reference + scale_ * tau[joint_q_index_[i]]);
  }
  return controller_interface::return_type::OK;
}

}  // namespace so101_gravity_comp

PLUGINLIB_EXPORT_CLASS(
  so101_gravity_comp::GravityCompensationController, controller_interface::ChainableControllerInterface)
