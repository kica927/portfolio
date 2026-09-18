"""식별한 회전 동역학(지연 τ + 1차 시정수 T + 게인 K) + 기록된 데드밴드 위에서 조향 제어기 세 가지를 비교한다.

  bang-bang : |오차| > 허용이면 ±0.4 rad/s (grippers 실기 방식), 아니면 0
  비례      : u = kp·오차, |u| ≤ 0.6, 데드밴드 보상(0 이 아니면 최소 0.35)
  MPC       : 1.5초 예측 선형 모델, |u| ≤ 0.6, 박스 제약 최소제곱으로 매 주기 풀이, 같은 데드밴드 보상

먼저 bag 명령을 시뮬레이터에 넣어 IMU 를 재현하는지(식별 R² 와 같은지) 확인한다.
"""
import math
import sys

import numpy as np
from scipy.optimize import lsq_linear

HOST_DT = 0.1
SIM_DT = 0.001
TOL = math.radians(5.0)
HOLD = 0.5
DEADBAND = 0.35
U_MAX = 0.6
BANG = 0.4


class Plant:
    """ω' = (K·u_eff(t-τ) - ω)/T, θ' = ω. u_eff 는 데드밴드 아래면 0."""

    def __init__(self, tau, T, K, deadband):
        self.tau, self.T, self.K, self.db = tau, T, K, deadband
        self.theta = self.omega = 0.0
        self.buf = [0.0] * max(1, int(round(tau / SIM_DT)))

    def step(self, u):
        self.buf.append(u)
        ud = self.buf.pop(0)
        ueff = 0.0 if abs(ud) < self.db else ud
        a = math.exp(-SIM_DT / self.T)
        self.omega = a * self.omega + (1 - a) * self.K * ueff
        self.theta += self.omega * SIM_DT


def with_deadband_comp(u):
    if u == 0.0:
        return 0.0
    return math.copysign(max(abs(u), DEADBAND), u)


def ctrl_bang(err, omega, prev, model):
    return math.copysign(BANG, err) if abs(err) > TOL else 0.0


def make_prop(kp):
    def ctrl(err, omega, prev, model):
        if abs(err) <= TOL:
            return 0.0
        return with_deadband_comp(float(np.clip(kp * err, -U_MAX, U_MAX)))
    return ctrl


def make_mpc(horizon=15, q=1.0, r=0.02, s=0.2):
    def ctrl(err, omega, prev, model):
        if abs(err) <= TOL:
            return 0.0
        _, T, K = model
        a = math.exp(-HOST_DT / T)
        b = K * (1 - a)
        # ω_{k+1} = a ω_k + b u_k ,  θ_{k+1} = θ_k + ω_k·dt  (θ 는 목표 대비 오차의 음수 방향)
        Aw = np.zeros((horizon, horizon))
        w0 = np.zeros(horizon)
        for k in range(horizon):
            w0[k] = (a ** (k + 1)) * omega
            for j in range(k + 1):
                Aw[k, j] = (a ** (k - j)) * b
        # 누적 회전: θ_k = Σ_{i<k} ω_i·dt,  ω_0 = 현재
        Ath = np.zeros((horizon, horizon))
        th0 = np.zeros(horizon)
        for k in range(horizon):
            th0[k] = omega * HOST_DT + (w0[:k].sum() * HOST_DT)
            if k > 0:
                Ath[k] = Aw[:k].sum(axis=0) * HOST_DT
        rows = [math.sqrt(q) * Ath, math.sqrt(r) * np.eye(horizon)]
        rhs = [math.sqrt(q) * (err - th0), np.zeros(horizon)]
        D = np.eye(horizon) - np.eye(horizon, k=-1)
        d0 = np.zeros(horizon); d0[0] = prev
        rows.append(math.sqrt(s) * D)
        rhs.append(math.sqrt(s) * d0)
        res = lsq_linear(np.vstack(rows), np.concatenate(rhs), bounds=(-U_MAX, U_MAX))
        return with_deadband_comp(float(res.x[0]))
    return ctrl


def run(ctrl, target, plant_params, model_params, duration=8.0):
    p = Plant(*plant_params, DEADBAND)
    u = 0.0
    switches, effort, overshoot = 0, 0.0, 0.0
    settled_at, in_since = None, None
    steps = int(round(HOST_DT / SIM_DT))
    for k in range(int(duration / HOST_DT)):
        t = k * HOST_DT
        err = target - p.theta
        new_u = ctrl(err, p.omega, u, model_params)
        if (new_u != 0.0) != (u != 0.0) or (new_u * u < 0):
            switches += 1
        u = new_u
        for _ in range(steps):
            p.step(u)
            overshoot = max(overshoot, math.copysign(1, target) * (p.theta - target))
        effort += abs(u) * HOST_DT
        if abs(target - p.theta) <= TOL:
            in_since = t if in_since is None else in_since
            if settled_at is None and t + HOST_DT - in_since >= HOLD:
                settled_at = in_since
        else:
            in_since = None
            settled_at = None
    final = abs(target - p.theta)
    return settled_at, math.degrees(max(0.0, overshoot)), switches, effort, math.degrees(final)


def validate_on_bag(bag, bias, tau, T, K):
    import rosbag2_py
    from rclpy.serialization import deserialize_message
    from rosidl_runtime_py.utilities import get_message
    topics = ["/cmd_vel", "/ros_robot_controller/imu_raw"]
    reader = rosbag2_py.SequentialReader()
    reader.open(rosbag2_py.StorageOptions(uri=bag, storage_id="sqlite3"), rosbag2_py.ConverterOptions("cdr", "cdr"))
    types = {t.name: t.type for t in reader.get_all_topics_and_types()}
    reader.set_filter(rosbag2_py.StorageFilter(topics=topics))
    cls = {t: get_message(types[t]) for t in topics}
    ct, cw, it, gz = [], [], [], []
    while reader.has_next():
        topic, data, stamp = reader.read_next()
        m = deserialize_message(data, cls[topic])
        if topic == "/cmd_vel":
            ct.append(stamp / 1e9); cw.append(m.angular.z)
        else:
            it.append(stamp / 1e9); gz.append(m.angular_velocity.z - bias)
    ct, cw, it, gz = map(np.array, (ct, cw, it, gz))
    out = {}
    for label, db in (("데드밴드 없음", 0.0), (f"데드밴드 {DEADBAND}", DEADBAND)):
        p = Plant(tau, T, K, db)
        t = it[0]
        pred = np.zeros(len(it))
        ci = 0
        for n, tn in enumerate(it):
            while t < tn:
                while ci + 1 < len(ct) and ct[ci + 1] <= t:
                    ci += 1
                p.step(cw[ci] if ct[ci] <= t else 0.0)
                t += SIM_DT
            pred[n] = p.omega
        out[label] = 1 - np.sum((gz - pred) ** 2) / np.sum((gz - gz.mean()) ** 2)
    return out


def main():
    bag = sys.argv[1] if len(sys.argv) > 1 else ""
    nominal = (0.02, 0.50, 0.935)
    if bag:
        r2 = validate_on_bag(bag, 0.00376, *nominal)
        print("시뮬레이터 검증 — bag 명령 재생 vs IMU 자이로 R²: " + " · ".join(f"{k} {v:.3f}" for k, v in r2.items()))

    controllers = {"bang-bang ±0.4": ctrl_bang, "비례 kp=1.0": make_prop(1.0), "비례 kp=2.0": make_prop(2.0), "MPC": make_mpc()}
    plants = {"공칭 T0.5 K0.93": (0.02, 0.50, 0.935), "느림 T0.8 K0.93": (0.02, 0.80, 0.935),
              "빠름 T0.3 K0.93": (0.02, 0.30, 0.935), "약함 T0.5 K0.80": (0.02, 0.50, 0.80)}
    print(f"\n허용 {math.degrees(TOL):.0f}° · {HOLD}s 유지하면 정착 · Host {1 / HOST_DT:.0f}Hz · 데드밴드 {DEADBAND} rad/s · 8초 제한")
    print("제어기는 항상 공칭 모델(T0.5 K0.93)을 가정하고, 실제 플랜트만 바꾼다")
    for pname, pp in plants.items():
        print(f"\n==== 실제 플랜트: {pname}")
        print(f"{'제어기':16s}{'목표':>6s}{'정착(s)':>9s}{'오버슈트°':>11s}{'명령전환':>9s}{'노력(rad)':>11s}{'최종오차°':>11s}")
        for cname, ctrl in controllers.items():
            for deg in (30, 90, 180):
                st, ov, sw, ef, fe = run(ctrl, math.radians(deg), pp, nominal)
                print(f"{cname:16s}{deg:6d}{('실패' if st is None else f'{st:.1f}'):>9s}{ov:11.1f}{sw:9d}{ef:11.2f}{fe:11.1f}")


if __name__ == "__main__":
    main()
