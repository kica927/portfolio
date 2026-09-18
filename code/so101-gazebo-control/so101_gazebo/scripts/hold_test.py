#!/usr/bin/env python3
"""/joint_states 를 기록해 팔이 자세를 얼마나 유지하는지 보고, 컨트롤러 전환 직후 초기 가속도를 모델 예측과 비교한다.

--switch-topic 을 주면 그 토픽(상위 컨트롤러 상태)이 끊긴 시각을 전환 시각으로 잡는다.
중력 보상 scale 이 s 일 때, 속도 0 에서의 초기 가속도는 q'' = M(q)^-1 (s - 1) g(q) 로 예측된다.
"""
import argparse
import os
import re
import time

import numpy as np
import rclpy
from control_msgs.msg import JointTrajectoryControllerState
from rclpy.node import Node
from rclpy.parameter import Parameter
from sensor_msgs.msg import JointState

ARM = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll"]
FIT_WINDOW = 0.15


class Hold(Node):
    def __init__(self, switch_topic):
        super().__init__("hold_test", parameter_overrides=[Parameter("use_sim_time", value=True)])
        self.rows = []
        self.last_ctrl_t = None
        self.create_subscription(JointState, "/joint_states", self.on_js, 1000)
        if switch_topic:
            self.create_subscription(JointTrajectoryControllerState, switch_topic, self.on_ctrl, 1000)

    def on_js(self, msg):
        names = list(msg.name)
        if not all(j in names for j in ARM):
            return
        t = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
        effort = [msg.effort[names.index(j)] if len(msg.effort) == len(names) else float("nan") for j in ARM]
        self.rows.append([t] + [msg.position[names.index(j)] for j in ARM] + effort)

    def on_ctrl(self, msg):
        self.last_ctrl_t = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9


def predicted_accel(q5, scale):
    import pinocchio as pin
    import xacro
    from ament_index_python.packages import get_package_share_directory
    src = os.path.join(get_package_share_directory("so101_moveit_config"), "config", "so101.urdf.xacro")
    urdf = re.sub(r"<ros2_control.*?</ros2_control>", "", xacro.process_file(src).toxml(), flags=re.S)
    model = pin.buildModelFromXML(urdf)
    data = model.createData()
    iq = [model.joints[model.getJointId(n)].idx_q for n in ARM]
    q = np.zeros(model.nq)
    q[iq] = q5
    M = pin.crba(model, data, q)
    M = np.triu(M) + np.triu(M, 1).T
    g = pin.computeGeneralizedGravity(model, data, q)
    return np.linalg.solve(M[np.ix_(iq, iq)], (scale - 1.0) * g[iq])


def row(label, values, fmt="15.2f"):
    return f"  {label:26s}" + "".join(f"{v:{fmt}}" for v in values)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=5.0)
    ap.add_argument("--out", default="")
    ap.add_argument("--switch-topic", default="")
    ap.add_argument("--scale", type=float, default=None)
    args = ap.parse_args()
    rclpy.init()
    node = Hold(args.switch_topic)
    wall_end = time.time() + 180
    while time.time() < wall_end:
        rclpy.spin_once(node, timeout_sec=0.02)
        if len(node.rows) < 2:
            continue
        start = node.rows[0][0]
        if args.switch_topic:
            if node.last_ctrl_t is None or node.rows[-1][0] - node.last_ctrl_t < 0.2:
                continue
            start = node.last_ctrl_t
        if node.rows[-1][0] - start >= args.seconds:
            break
    a = np.array(node.rows)
    if len(a) < 10:
        print("  joint_states 수신 부족")
        return 1
    if args.out:
        np.savetxt(args.out, a, delimiter=",", header="t," + ",".join(ARM) + ","
                   + ",".join(f"effort_{j}" for j in ARM), comments="")

    t_switch = node.last_ctrl_t if (args.switch_topic and node.last_ctrl_t is not None) else a[0, 0]
    before = a[(a[:, 0] >= t_switch - 0.1) & (a[:, 0] < t_switch)][:, :6]
    after_full = a[a[:, 0] >= t_switch]
    after = after_full[:, :6]
    t = after[:, 0] - t_switch
    print(f"  전환 시각 기준 전 {len(before)}개 · 후 {len(after)}개 (후 구간 {t[-1]:.2f}s)")
    print(f"  {'':26s}" + "".join(f"{j:>15s}" for j in ARM))
    q_switch = after[0, 1:]
    print(row("전환 순간 자세 (rad)", q_switch, "15.4f"))
    if len(before) > 5:
        vb = np.polyfit(before[:, 0] - t_switch, before[:, 1:], 1)[0]
        print(row("전환 전 0.1s 속도 (mrad/s)", vb * 1000))
    print(row("끝 자세 (rad)", after[-1, 1:], "15.4f"))
    print(row("최대 |변화| (mrad)", np.abs(after[:, 1:] - q_switch).max(0) * 1000))
    w = t <= FIT_WINDOW
    fit = np.polyfit(t[w], after[w, 1:], 2)
    measured = 2 * fit[0]
    print(row(f"측정 초기 가속도 (rad/s²)", measured, "15.3f"))
    v = np.gradient(after[:, 1:], after[:, 0], axis=0)
    k50 = min(int(np.searchsorted(t, 0.05)), len(after) - 1)
    kick = float(np.abs(v[k50]).max())
    print(f"  전환 50ms 후 최대 관절 속도 {kick:.4f} rad/s → {'킥 있음' if kick > 0.01 else '킥 없음'}")
    full_t = a[:, 0] - t_switch
    win = (full_t >= -0.004) & (full_t <= 0.006)
    if np.isfinite(a[win, 6:]).any():
        print("  전환 ±5ms 관절 effort (N·m) — t(ms) | " + " | ".join(ARM))
        for r in a[win]:
            print(f"    {(r[0] - t_switch) * 1000:+6.1f} | " + " | ".join(f"{x:+.4f}" for x in r[6:]))
    if args.scale is not None:
        pred = predicted_accel(q_switch, args.scale)
        print(row(f"예측 (scale={args.scale}) (rad/s²)", pred, "15.3f"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
