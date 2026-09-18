"""ICP 회전 과소추정의 원인이 로봇 자기 구조물인지, 초기값 문제인지 조건을 바꿔 비교한다."""
import math
import sys
from multiprocessing import Pool

import numpy as np
from scipy.spatial import cKDTree

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import lidar_odometry as lo

N_PAIRS = 1000


def icp(src, tgt, R0, iters=30):
    tree = cKDTree(tgt)
    R, t = R0.copy(), np.zeros(2)
    for i in range(iters):
        p = src @ R.T + t
        d, j = tree.query(p)
        m = d < max(0.05, 0.3 * (1 - i / iters))
        if m.sum() < 30:
            return None
        A, B = p[m], tgt[j[m]]
        ca, cb = A.mean(0), B.mean(0)
        U, _, Vt = np.linalg.svd((A - ca).T @ (B - cb))
        Ri = Vt.T @ U.T
        if np.linalg.det(Ri) < 0:
            Vt[1] *= -1
            Ri = Vt.T @ U.T
        R, t = Ri @ R, Ri @ t + (cb - Ri @ ca)
    return R, t


def static_angle_mask(scans):
    rows = []
    for _, r, a in scans:
        ok = np.isfinite(r) & (r > 0)
        b = np.floor(np.degrees(a)).astype(int) % 360
        s = np.bincount(b[ok], weights=r[ok], minlength=360)
        n = np.bincount(b[ok], minlength=360)
        rows.append(np.where(n > 0, s / np.maximum(n, 1), np.nan))
    R = np.vstack(rows)
    valid = np.mean(np.isfinite(R), axis=0)
    iqr = np.nanpercentile(R, 75, axis=0) - np.nanpercentile(R, 25, axis=0)
    med = np.nanmedian(R, axis=0)
    return (valid > 0.8) & (iqr < 0.03) & (med < 3.0)


def run(args):
    label, uri, r_min, use_angle_mask, imu_init = args
    name = uri.rstrip("/").split("/")[-1]
    scans, ct, cv, it, gz = lo.read(uri)
    gz = gz - lo.BIAS[name]
    scans = scans[:N_PAIRS + 1]
    bad_bins = static_angle_mask(scans) if use_angle_mask else np.zeros(360, bool)

    def xy(r, a):
        b = np.floor(np.degrees(a)).astype(int) % 360
        ok = np.isfinite(r) & (r > r_min) & (r < lo.MAX_R) & ~bad_bins[b]
        return np.c_[r[ok] * np.cos(a[ok]), r[ok] * np.sin(a[ok])]

    pts = [xy(r, a) for _, r, a in scans]
    st = np.array([s[0] for s in scans])
    dimu_dt = float(np.median(np.diff(it)))
    d_icp, d_imu, trans, fwd_ok, speed_dt = [], [], [], [], []
    for k in range(len(scans) - 1):
        m = (it >= st[k]) & (it < st[k + 1])
        di = float(np.sum(gz[m]) * dimu_dt) if m.any() else 0.0
        R0 = np.array([[math.cos(di), -math.sin(di)], [math.sin(di), math.cos(di)]]) if imu_init else np.eye(2)
        res = icp(pts[k + 1], pts[k], R0)
        if res is None:
            continue
        R, t = res
        d_icp.append(math.atan2(R[1, 0], R[0, 0])); d_imu.append(di); trans.append(t)
        ci = np.searchsorted(ct, st[k] - 0.5, side="right") - 1
        cj = np.searchsorted(ct, st[k + 1], side="right") - 1
        steady = ci >= 0 and np.all(cv[ci:cj + 1] == cv[cj])
        fwd_ok.append(bool(steady and np.isclose(cv[cj, 0], 0.1) and cv[cj, 1] == 0 and abs(di) < 0.01))
        speed_dt.append(st[k + 1] - st[k])
    d_icp, d_imu = np.array(d_icp), np.array(d_imu)
    trans, fwd_ok, speed_dt = np.array(trans), np.array(fwd_ok), np.array(speed_dt)
    slope = float(np.dot(d_icp, d_imu) / np.dot(d_imu, d_imu))
    corr = float(np.corrcoef(d_icp, d_imu)[0, 1])
    turning = np.abs(d_imu) > 0.02
    slope_turn = float(np.dot(d_icp[turning], d_imu[turning]) / np.dot(d_imu[turning], d_imu[turning]))
    ang = np.arctan2(trans[fwd_ok, 1], trans[fwd_ok, 0])
    heading = math.degrees(math.atan2(np.mean(np.sin(ang)), np.mean(np.cos(ang)))) % 360
    speed = float(np.median(np.hypot(trans[fwd_ok, 0], trans[fwd_ok, 1]) / speed_dt[fwd_ok]))
    return (label, len(d_icp), int(np.mean([len(p) for p in pts])), slope, slope_turn, corr, heading, speed, int(fwd_ok.sum()))


if __name__ == "__main__":
    uri = sys.argv[1]
    cases = [
        ("기준 r>0.12", uri, 0.12, False, False),
        ("r>0.25", uri, 0.25, False, False),
        ("r>0.40", uri, 0.40, False, False),
        ("r>0.12 + 고정각도 제외", uri, 0.12, True, False),
        ("r>0.12 + IMU 초기값", uri, 0.12, False, True),
        ("r>0.40 + 고정각도 제외 + IMU 초기값", uri, 0.40, True, True),
    ]
    with Pool(3) as pool:
        results = pool.map(run, cases)
    print(f"앞 {N_PAIRS}개 스캔쌍 · 회전 기울기는 ICP/IMU (1이면 일치)")
    print(f"{'조건':38s}{'쌍':>6s}{'점수':>6s}{'기울기':>9s}{'회전중':>9s}{'상관':>8s}{'전진방향°':>11s}{'전진속도':>10s}{'직진쌍':>7s}")
    for label, n, npts, s, st_, c, h, v, nf in results:
        print(f"{label:38s}{n:6d}{npts:6d}{s:9.3f}{st_:9.3f}{c:8.3f}{h:11.1f}{v:10.4f}{nf:7d}")
