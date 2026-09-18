"""hold_test.py 에 관절 effort 기록과 전환 순간 토크·속도 킥 판정을 추가한다."""
p = "/home/lemma/so101_ws/src/so101_gazebo/scripts/hold_test.py"
src = open(p).read()

old = "        self.rows.append([t] + [msg.position[names.index(j)] for j in ARM])\n"
new = ("        effort = [msg.effort[names.index(j)] if len(msg.effort) == len(names) else float(\"nan\") for j in ARM]\n"
       "        self.rows.append([t] + [msg.position[names.index(j)] for j in ARM] + effort)\n")
assert old in src
src = src.replace(old, new)

old = '        np.savetxt(args.out, a, delimiter=",", header="t," + ",".join(ARM), comments="")\n'
new = ('        np.savetxt(args.out, a, delimiter=",", header="t," + ",".join(ARM) + ","\n'
       '                   + ",".join(f"effort_{j}" for j in ARM), comments="")\n')
assert old in src
src = src.replace(old, new)

src = src.replace("before = a[(a[:, 0] >= t_switch - 0.1) & (a[:, 0] < t_switch)]",
                  "before = a[(a[:, 0] >= t_switch - 0.1) & (a[:, 0] < t_switch)][:, :6]")
src = src.replace("after = a[a[:, 0] >= t_switch]", "after_full = a[a[:, 0] >= t_switch]\n    after = after_full[:, :6]")

old = "    if args.scale is not None:\n"
new = '''    v = np.gradient(after[:, 1:], after[:, 0], axis=0)
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
'''
assert old in src
src = src.replace(old, new, 1)
open(p, "w").write(src)
print("hold_test.py 패치 완료")
