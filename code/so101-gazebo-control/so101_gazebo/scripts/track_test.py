#!/usr/bin/env python3
"""FollowJointTrajectory 로 표준 테스트 궤적을 보내고, 컨트롤러 상태에서 추종 오차를 기록·요약한다."""
import argparse
import csv
import math
import time

import numpy as np
import rclpy
from builtin_interfaces.msg import Duration
from control_msgs.action import FollowJointTrajectory
from control_msgs.msg import JointTrajectoryControllerState
from moveit_msgs.action import MoveGroup
from moveit_msgs.msg import Constraints, JointConstraint
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.parameter import Parameter
from trajectory_msgs.msg import JointTrajectoryPoint

JOINTS = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll"]
POSE_A = [0.8, -0.8, 0.9, 0.6, 0.5]
POSE_B = [-0.6, -1.1, 1.0, 0.2, -0.5]
SINE_BASE = [0.0, -0.6, 0.8, 0.3, 0.0]

# 요약 구간(궤적 시작 기준 초): 정상상태 창, 동적 창
WINDOWS = {
    "step": {"정상상태_A": (2.2, 3.0), "정상상태_B": (5.7, 6.5), "전체": (0.0, 6.5)},
    "toA": {"정상상태_A": (1.2, 2.0), "전체": (0.0, 2.0)},
    "moveit": {"전체": (0.0, 1e9)},
    "sine": {"사인 추종": (2.0, 7.5), "전체": (0.0, 7.5)},
}


def dur(t):
    return Duration(sec=int(t), nanosec=int(round((t - int(t)) * 1e9)))


def point(t, pos, vel=None, acc=None):
    p = JointTrajectoryPoint()
    p.time_from_start = dur(t)
    p.positions = [float(v) for v in pos]
    p.velocities = [float(v) for v in (vel if vel is not None else [0.0] * len(pos))]
    p.accelerations = [float(v) for v in (acc if acc is not None else [0.0] * len(pos))]
    return p


def step_profile():
    return [point(1.0, POSE_A), point(3.0, POSE_A), point(4.5, POSE_B), point(6.5, POSE_B)]


def to_a_profile():
    return [point(1.0, POSE_A), point(2.0, POSE_A)]


def sine_profile(amp=0.5, freq=0.5, duration=6.0, rate=50):
    w = 2 * math.pi * freq
    pts = [point(1.5, SINE_BASE)]
    for k in range(1, int(duration * rate) + 1):
        t = k / rate
        pos, vel, acc = list(SINE_BASE), [0.0] * 5, [0.0] * 5
        for i, sign in ((1, 1.0), (2, -1.0)):
            pos[i] = SINE_BASE[i] + sign * amp * (1 - math.cos(w * t))
            vel[i] = sign * amp * w * math.sin(w * t)
            acc[i] = sign * amp * w * w * math.cos(w * t)
        pts.append(point(1.5 + t, pos, vel, acc))
    return pts


class Tester(Node):
    def __init__(self):
        super().__init__("track_tester", parameter_overrides=[Parameter("use_sim_time", value=True)])
        self.rows = []
        self.recording = False
        self.got_state = False
        self.create_subscription(JointTrajectoryControllerState, "/arm_controller/controller_state", self.on_state, 1000)
        self.client = ActionClient(self, FollowJointTrajectory, "/arm_controller/follow_joint_trajectory")
        self.move_client = ActionClient(self, MoveGroup, "/move_action")

    def on_state(self, msg):
        self.got_state = True
        if not self.recording:
            return
        names = list(msg.joint_names)
        idx = [names.index(j) for j in JOINTS]

        def pick(values):
            return [values[i] if len(values) > i else float("nan") for i in idx]

        output = msg.output.effort if len(msg.output.effort) else msg.output.positions
        t = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
        self.rows.append([t] + pick(msg.reference.positions) + pick(msg.feedback.positions)
                         + pick(msg.error.positions) + pick(output) + pick(msg.feedback.velocities))


def moveit_goal(pose, velocity_scale=0.5):
    goal = MoveGroup.Goal()
    req = goal.request
    req.group_name = "arm"
    req.num_planning_attempts = 5
    req.allowed_planning_time = 5.0
    req.max_velocity_scaling_factor = velocity_scale
    req.max_acceleration_scaling_factor = velocity_scale
    req.goal_constraints = [Constraints(joint_constraints=[
        JointConstraint(joint_name=j, position=float(v), tolerance_above=0.005, tolerance_below=0.005, weight=1.0)
        for j, v in zip(JOINTS, pose)])]
    goal.planning_options.plan_only = False
    return goal


def run_moveit(node):
    if not node.move_client.wait_for_server(timeout_sec=60.0):
        print("  /move_action 서버 없음")
        return False
    end = time.time() + 30.0
    while not node.got_state and time.time() < end:
        rclpy.spin_once(node, timeout_sec=0.05)
    if not node.got_state:
        print("  컨트롤러 상태 토픽을 받지 못함")
        return False
    node.recording = True
    for label, pose in (("A", POSE_A), ("B", POSE_B)):
        send = node.move_client.send_goal_async(moveit_goal(pose))
        rclpy.spin_until_future_complete(node, send, timeout_sec=30.0)
        handle = send.result()
        if handle is None or not handle.accepted:
            print(f"  [{label}] MoveGroup 목표 거부")
            return False
        result = handle.get_result_async()
        rclpy.spin_until_future_complete(node, result, timeout_sec=120.0)
        if not result.done():
            print(f"  [{label}] 결과 대기 시간 초과")
            return False
        r = result.result().result
        traj = r.planned_trajectory.joint_trajectory
        dur = traj.points[-1].time_from_start.sec + traj.points[-1].time_from_start.nanosec * 1e-9 if traj.points else 0.0
        print(f"  [{label}] MoveIt 결과 코드 {r.error_code.val} · 계획 {r.planning_time:.2f}s · 궤적 점 {len(traj.points)}개 · 궤적 길이 {dur:.2f}s")
        if r.error_code.val != 1:
            return False
        end = time.time() + 1.0
        while time.time() < end:
            rclpy.spin_once(node, timeout_sec=0.05)
    node.recording = False
    return True


def summarize(rows, profile):
    a = np.array(rows)
    t = a[:, 0] - a[0, 0]
    n = len(JOINTS)
    err = a[:, 1 + 2 * n:1 + 3 * n]
    out = a[:, 1 + 3 * n:1 + 4 * n]
    print(f"  기록 {len(a)}행 · 기록 주기 {len(a) / max(t[-1], 1e-9):.1f}Hz")
    header = "".join(f"{j:>15s}" for j in JOINTS)
    for label, (t0, t1) in WINDOWS[profile].items():
        m = (t >= t0) & (t < t1)
        if not m.any():
            continue
        print(f"  [{label}] {t0}~{t1}s")
        print(f"    {'':22s}{header}")
        print(f"    {'평균 오차 (mrad)':22s}" + "".join(f"{v * 1000:15.2f}" for v in err[m].mean(0)))
        print(f"    {'RMS 오차 (mrad)':22s}" + "".join(f"{v * 1000:15.2f}" for v in np.sqrt((err[m] ** 2).mean(0))))
        print(f"    {'최대 |오차| (mrad)':22s}" + "".join(f"{v * 1000:15.2f}" for v in np.abs(err[m]).max(0)))
        print(f"    {'최대 |출력|':22s}" + "".join(f"{v:15.3f}" for v in np.nanmax(np.abs(out[m]), 0)))
        vel = a[:, 1 + 4 * n:1 + 5 * n]
        print(f"    {'최대 |속도| (rad/s)':22s}" + "".join(f"{v:15.3f}" for v in np.nanmax(np.abs(vel[m]), 0)))
    fb = a[:, 1 + n:1 + 2 * n]
    print(f"  마지막 피드백 위치 (rad): " + " ".join(f"{v:+.3f}" for v in fb[-1]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", choices=["step", "sine", "toA", "moveit"], default="step")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    rclpy.init()
    node = Tester()
    if args.profile == "moveit":
        ok = run_moveit(node)
        n = len(JOINTS)
        with open(args.out, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["t"] + [f"ref_{j}" for j in JOINTS] + [f"fb_{j}" for j in JOINTS] + [f"err_{j}" for j in JOINTS]
                       + [f"out_{j}" for j in JOINTS] + [f"vel_{j}" for j in JOINTS])
            w.writerows(node.rows)
        if node.rows:
            summarize(node.rows, "moveit")
        node.destroy_node()
        rclpy.shutdown()
        return 0 if ok else 1
    if not node.client.wait_for_server(timeout_sec=60.0):
        print("액션 서버 없음")
        return 1

    goal = FollowJointTrajectory.Goal()
    goal.trajectory.joint_names = JOINTS
    goal.trajectory.points = {"step": step_profile, "sine": sine_profile, "toA": to_a_profile}[args.profile]()

    node.recording = True
    send = node.client.send_goal_async(goal)
    rclpy.spin_until_future_complete(node, send)
    handle = send.result()
    if not handle.accepted:
        print("목표 거부됨")
        return 1
    last = goal.trajectory.points[-1].time_from_start
    traj_len = last.sec + last.nanosec * 1e-9
    wait = traj_len * 3 + 20
    wall0 = time.time()
    result = handle.get_result_async()
    rclpy.spin_until_future_complete(node, result, timeout_sec=wait)
    if result.done():
        end = time.time() + 1.0
        while time.time() < end:
            rclpy.spin_once(node, timeout_sec=0.05)
    node.recording = False
    wall = time.time() - wall0

    if result.done():
        res = result.result().result
        print(f"  결과 코드 {res.error_code} {res.error_string!r}")
    else:
        print(f"  결과 대기 {wait:.0f}s 초과 — 목표 취소, 부분 기록으로 요약")
        cancel = handle.cancel_goal_async()
        rclpy.spin_until_future_complete(node, cancel, timeout_sec=5.0)
    if node.rows:
        sim = node.rows[-1][0] - node.rows[0][0]
        print(f"  시뮬 시간 {sim:.2f}s / 실제 시간 {wall:.2f}s → 속도 배율(RTF) 약 {sim / max(wall, 1e-9):.3f}")
    n = len(JOINTS)
    with open(args.out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["t"] + [f"ref_{j}" for j in JOINTS] + [f"fb_{j}" for j in JOINTS] + [f"err_{j}" for j in JOINTS]
                   + [f"out_{j}" for j in JOINTS] + [f"vel_{j}" for j in JOINTS])
        w.writerows(node.rows)
    if node.rows:
        summarize(node.rows, args.profile)
    node.destroy_node()
    rclpy.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
