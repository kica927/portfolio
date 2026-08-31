"""A1 in-process 실험 — UdpHostLink._parse 가 방어층 D5 인가.

실제 UdpHostLink 를 로컬 루프백(127.0.0.1)에 띄우고 손상 패킷을 쏜다.
하드웨어도 Host 도 필요 없다 — 소켓 하나면 된다.

겨누는 불변식:
    I4 낡은/불량 명령은 거부되거나 안전하게 처리된다
    D5 손상 패킷 폐기 — 반쯤 읽어 0으로 채우지 않는다
"""

import inspect
import socket
import time

import harness  # noqa: F401
import protocol as P
from domain.adapters.real.udp_host_link import UdpHostLink


def check(name, ok, detail=""):
    mark = "PASS" if ok else "**FAIL**"
    print(f"  [{mark}] {name}" + (f"  — {detail}" if detail else ""))
    return ok


def _send(sock, port, payload):
    sock.sendto(payload, ("127.0.0.1", port))
    time.sleep(0.03)


def run():
    print("A1 — UdpHostLink._parse (D5 손상 패킷 폐기), 로컬 루프백")
    results = []
    # 명령 포트를 임시 포트로 띄워 5005 충돌을 피한다.
    port = 45005
    # follow_commander 는 host-link 계열(smolVLA·sysy009 host-link)에만 있는
    # 인자다. baseline 에는 없으므로 시그니처를 보고 있을 때만 넘긴다 —
    # 그래야 baseline·host-link 어느 브랜치에서도 이 probe 가 돈다.
    _kw = {"command_port": port}
    if "follow_commander" in inspect.signature(UdpHostLink).parameters:
        _kw["follow_commander"] = False
    link = UdpHostLink("127.0.0.1", **_kw)
    tx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        corrupt = [
            (b"\xff\xfe not utf8", "비 UTF-8"),
            (b"{bad json", "깨진 JSON"),
            (b"{}", "state 없음"),
            (P.raw({"state": 123}), "state 수치"),
            (P.raw({"state": "APPROACH", "linear_x": "fast"}), "속도 문자열"),
            (b"", "빈 페이로드"),
        ]
        for payload, note in corrupt:
            _send(tx, port, payload)
            got = link.latest_command()
            results.append(check(f"손상 폐기: {note}", got is None,
                                 "None 이어야 (정지 아님)" if got is None else f"통과됨! {got}"))

        # 유효 명령은 통과해야 한다 (대조군)
        _send(tx, port, P.command("APPROACH", linear_x=0.1))
        got = link.latest_command()
        results.append(check("대조군: 유효 명령 통과", got is not None and got.state == "APPROACH",
                             f"{got}"))

        # NaN — 유효한 JSON float 라 _parse 를 통과한다. 이것이 결함 후보다.
        _send(tx, port, b'{"state":"APPROACH","linear_x":NaN,"linear_y":0,"angular_z":0,"stop":false}')
        got = link.latest_command()
        leaked = got is not None and got.linear_x != got.linear_x  # nan != nan
        results.append(check("NaN 은 _parse 를 통과한다(예상된 구멍)", leaked,
                             "linear_x=nan 이 그대로 통과 — 클램프도 못 막음(probe_motion 참고)"
                             if leaked else "막힘(설계가 바뀌었는지 확인)"))
    finally:
        link.close()
        tx.close()
    return results


if __name__ == "__main__":
    rs = run()
    print(f"\n{sum(rs)}/{len(rs)} 통과")
    raise SystemExit(0 if all(rs) else 1)
