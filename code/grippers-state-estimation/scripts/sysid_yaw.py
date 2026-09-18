"""회전 명령 → IMU 자이로 z 응답을 '순수 지연 + 1차 지연 + 게인' 모델로 식별하고 교차검증한다."""
import sys

import numpy as np
import rosbag2_py
from rclpy.serialization import deserialize_message
from rosidl_runtime_py.utilities import get_message
from scipy.signal import lfilter

TAUS = np.arange(0.0, 0.52, 0.02)
TCS = np.arange(0.02, 1.52, 0.02)


def read(uri):
    topics = ["/cmd_vel", "/ros_robot_controller/imu_raw"]
    reader = rosbag2_py.SequentialReader()
    reader.open(rosbag2_py.StorageOptions(uri=uri, storage_id="sqlite3"),
                rosbag2_py.ConverterOptions("cdr", "cdr"))
    types = {t.name: t.type for t in reader.get_all_topics_and_types()}
    reader.set_filter(rosbag2_py.StorageFilter(topics=topics))
    classes = {t: get_message(types[t]) for t in topics}
    ct, cv, it, gz = [], [], [], []
    while reader.has_next():
        topic, data, stamp = reader.read_next()
        m = deserialize_message(data, classes[topic])
        if topic == "/cmd_vel":
            ct.append(stamp / 1e9); cv.append((m.linear.x, m.angular.z))
        else:
            it.append(stamp / 1e9); gz.append(m.angular_velocity.z)
    return np.array(ct), np.array(cv), np.array(it), np.array(gz)


def still_bias(ct, cv, it, gz):
    change = np.concatenate([[True], np.any(np.diff(cv, axis=0) != 0, axis=1)])
    starts = np.where(change)[0]
    ends_t = np.concatenate([ct[starts[1:]], [it[-1]]])
    mask = np.zeros_like(it, dtype=bool)
    for s, t1 in zip(starts, ends_t):
        t0 = ct[s]
        if np.all(cv[s] == 0) and t1 - t0 >= 2.0:
            mask |= (it >= t0 + 0.3) & (it < t1)
    return float(np.mean(gz[mask])), int(mask.sum())


def held_input(ct, cw, it, tau):
    idx = np.searchsorted(ct, it - tau, side="right") - 1
    return np.where(idx >= 0, cw[np.clip(idx, 0, None)], 0.0)


def unit_response(u, dt, tc):
    a = np.exp(-dt / tc)
    return lfilter([1 - a], [1, -a], u)


def r2(y, yhat):
    return 1 - np.sum((y - yhat) ** 2) / np.sum((y - np.mean(y)) ** 2)


def best_k(x, y):
    return float(np.dot(x, y) / np.dot(x, x))


def fit(bag):
    ct, cw, it, y, dt = bag
    best = None
    for tau in TAUS:
        u = held_input(ct, cw, it, tau)
        for tc in TCS:
            x = unit_response(u, dt, tc)
            k = best_k(x, y)
            sse = float(np.sum((y - k * x) ** 2))
            if best is None or sse < best[0]:
                best = (sse, tau, tc, k)
    return best[1:]


def predict(bag, params):
    ct, cw, it, _, dt = bag
    tau, tc, k = params
    return k * unit_response(held_input(ct, cw, it, tau), dt, tc)


def main(uris):
    bags, names = [], []
    for uri in uris:
        ct, cv, it, gz = read(uri)
        bias, n = still_bias(ct, cv, it, gz)
        dt = float(np.median(np.diff(it)))
        bags.append((ct, cv[:, 1], it, gz - bias, dt))
        names.append(uri.rstrip("/").split("/")[-1])
        print(f"==== {names[-1]} · 바이어스 {bias:.5f} rad/s (정지 샘플 {n}개) · IMU dt 중앙값 {dt * 1000:.2f}ms")

    params = []
    for name, bag in zip(names, bags):
        ct, cw, it, y, dt = bag
        p = fit(bag)
        params.append(p)
        naive = held_input(ct, cw, it, 0.0)
        print(f"  [{name}] 식별: τ={p[0]:.2f}s · T={p[1]:.2f}s · K={p[2]:.3f} · R²={r2(y, predict(bag, p)):.3f}"
              f"   |  '명령=실제' R²={r2(y, naive):.3f}")
        d = np.diff(it)
        print(f"    총 yaw 변화(rad) IMU {np.sum(y[:-1] * d):.3f} · 명령 적분 {np.sum(naive[:-1] * d):.3f} · "
              f"모델 {np.sum(predict(bag, p)[:-1] * d):.3f}")

    if len(bags) == 2:
        for i, j in ((0, 1), (1, 0)):
            print(f"  교차검증: {names[i]} 파라미터 → {names[j]} R²={r2(bags[j][3], predict(bags[j], params[i])):.3f}")

    for name, bag, p in zip(names, bags, params):
        ct, cw, it, y, dt = bag
        u = held_input(ct, cw, it, p[0])
        prof = []
        for tc in (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.8, 1.0, 1.4):
            x = unit_response(u, dt, tc)
            k = best_k(x, y)
            prof.append(f"T={tc:.1f}:{r2(y, k * x):.3f}(K={k:.2f})")
        print(f"  [{name}] τ={p[0]:.2f} 고정 T 프로파일: " + "  ".join(prof))


if __name__ == "__main__":
    main(sys.argv[1:])
