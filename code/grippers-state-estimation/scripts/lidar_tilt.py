"""로봇에 고정된 거리 패턴(바닥 교차)을 찾아 LiDAR 기울기를 역추정한다."""
import sys

import numpy as np
import rosbag2_py
from rclpy.serialization import deserialize_message
from rosidl_runtime_py.utilities import get_message
from scipy.optimize import least_squares

H_NOMINAL = 0.07 + 0.0925


def load_scans(uri):
    reader = rosbag2_py.SequentialReader()
    reader.open(rosbag2_py.StorageOptions(uri=uri, storage_id="sqlite3"),
                rosbag2_py.ConverterOptions("cdr", "cdr"))
    types = {t.name: t.type for t in reader.get_all_topics_and_types()}
    reader.set_filter(rosbag2_py.StorageFilter(topics=["/scan_raw"]))
    cls = get_message(types["/scan_raw"])
    rows, counts = [], set()
    while reader.has_next():
        _, data, _ = reader.read_next()
        m = deserialize_message(data, cls)
        r = np.asarray(m.ranges, dtype=float)
        counts.add(len(r))
        ok = np.isfinite(r) & (r > m.range_min) & (r < m.range_max)
        deg = np.degrees(m.angle_min + m.angle_increment * np.arange(len(r)))
        b = np.floor(deg).astype(int) % 360
        s = np.bincount(b[ok], weights=r[ok], minlength=360)
        n = np.bincount(b[ok], minlength=360)
        rows.append(np.where(n > 0, s / np.maximum(n, 1), np.nan))
    print("  스캔당 점 개수 종류:", sorted(counts))
    return np.vstack(rows)


def main(uri):
    R = load_scans(uri)
    ang = np.arange(360) + 0.5
    valid = np.mean(np.isfinite(R), axis=0)
    med = np.nanmedian(R, axis=0)
    iqr = np.nanpercentile(R, 75, axis=0) - np.nanpercentile(R, 25, axis=0)

    print(f"  스캔 {R.shape[0]}개 × 1° 칸 360개")
    print("  30° 구간별 요약 (각도: 유효율 / 거리 중앙값 m / IQR m)")
    for a0 in range(0, 360, 30):
        m = (ang >= a0) & (ang < a0 + 30)
        print(f"    {a0:3d}~{a0 + 30:3d}°: {np.mean(valid[m]):.2f} / {np.nanmedian(med[m]):.3f} / {np.nanmedian(iqr[m]):.3f}")

    fixed = (valid > 0.8) & (iqr < 0.03) & (med < 3.0)
    print(f"  시간에 따라 거의 안 변하는 방향(유효율>0.8, IQR<3cm, 3m 이내): {int(fixed.sum())}개")
    if fixed.sum() < 8:
        print("  고정 거리 패턴이 부족해 기울기 피팅 불가")
        return
    fa, fr = np.radians(ang[fixed]), med[fixed]
    fdeg = ang[fixed]
    groups = np.split(fdeg, np.where(np.diff(fdeg) > 3)[0] + 1)
    print("  고정 패턴 각도 범위:", [(float(g[0]), float(g[-1]), len(g)) for g in groups])
    print("  고정 패턴 거리 최소/중앙/최대:", np.round([fr.min(), np.median(fr), fr.max()], 3))

    def model(p, a, h):
        c = np.cos(a - p[1])
        return h / (np.tan(p[0]) * np.clip(c, 1e-3, None))

    best = None
    for th0 in np.radians(np.arange(0, 360, 30)):
        res = least_squares(lambda p: model(p, fa, H_NOMINAL) - fr, x0=[np.radians(10), th0],
                            bounds=([np.radians(1), -np.inf], [np.radians(45), np.inf]))
        if best is None or res.cost < best.cost:
            best = res
    resid = model(best.x, fa, H_NOMINAL) - fr
    print(f"  [h={H_NOMINAL:.4f}m 고정] 기울기 {np.degrees(best.x[0]):.2f}° · 가장 아래를 보는 방향 "
          f"{np.degrees(best.x[1]) % 360:.1f}° · 잔차 RMS {np.sqrt(np.mean(resid ** 2)) * 100:.2f}cm")

    res_h = least_squares(lambda p: model(p[:2], fa, p[2]) - fr, x0=[best.x[0], best.x[1], H_NOMINAL],
                          bounds=([np.radians(1), -np.inf, 0.05], [np.radians(45), np.inf, 0.4]))
    resid_h = model(res_h.x[:2], fa, res_h.x[2]) - fr
    print(f"  [h 자유] 기울기 {np.degrees(res_h.x[0]):.2f}° · 방향 {np.degrees(res_h.x[1]) % 360:.1f}° · "
          f"높이 {res_h.x[2]:.4f}m · 잔차 RMS {np.sqrt(np.mean(resid_h ** 2)) * 100:.2f}cm")
    print(f"  참고: 11.3° 기울기일 때 정면 바닥 교차 거리 {H_NOMINAL / np.tan(np.radians(11.3)):.3f}m")


if __name__ == "__main__":
    for uri in sys.argv[1:]:
        print("====", uri)
        main(uri)
