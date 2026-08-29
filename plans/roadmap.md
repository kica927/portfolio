# 로드맵 — 보안 연구로 가는 길

> **2026-09 ~ 2027-02 · 주 20시간 · 이 맥(Apple M1 Pro / arm64)에서 실행 가능하게 짠 계획**
>
> 실행 환경과 도구별 가부는 [`mac-environment.md`](mac-environment.md) 에
> 실측으로 정리해 두었습니다. 아래 모든 작업에는 **A / B1 / B2 / C / D** 표시가
> 붙어 있습니다 — 어디서 도는지를 뜻합니다.

| | 환경 |
|---|---|
| **A** | 맥 네이티브 (arm64) |
| **B1** | linux/arm64 컨테이너 — 네이티브 속도 |
| **B2** | linux/amd64 컨테이너 — Rosetta, 느림 |
| **C** | 브라우저 (pwn.college) |
| **D** | 라즈베리파이 5 실기 — ⚠️ **2026-09-08 까지만** |

> 🔴 **하드웨어 접근이 2026-09-08 에 끝납니다.** 그 이후 D 는 존재하지 않고,
> 모든 실기 검증은 **그 전에 녹화한 데이터**로 대체됩니다.
> 남은 10일에 반드시 확보할 것 → [`2026-09-08-capture.md`](2026-09-08-capture.md)

---

## 한 문장

> **공부 자체를 포트폴리오로 만들지 않고, 공부 → 실습 → 분석 → 실제 시스템 적용 →
> 실험 결과라는 연속된 증거를 만든다.**

## 기술 축

```
Math / Electronics / 5G
          ↓
C → CS:APP → OSTEP → Security → Binary Analysis → Fuzzing
                                                     ↓
                                                  RoboSec
```

---

## 현재 위치

| | 프로젝트 | 상태 |
|---|---|---|
| ✅ | [grippers](../projects/grippers.md) | 완료 — 실기 검증까지 |
| ✅ | [grippers-host-mac](../projects/grippers-host-mac.md) | 완료 |
| ✅ | [Immortan 자율주행](../projects/immortan-self-driving.md) | 🥇 1등 (2026-07) |
| ✅ | [Geti F1 분류](../projects/geti-f1-classification.md) | 58% → 91% (2026-08) |
| ✅ | [LeRobot 모방학습](../projects/lerobot-imitation.md) | 파이프라인 동작 (2026-08) |
| ✅ | [5G/UDP 프로토타입](../projects/5g-udp-prototype.md) | 2023 (코드 비공개) |
| ✅ | [Pell 방정식 연구](../projects/pell-equations.md) | 2022 |
| 🔴 | **[로봇 마지막 10일 수집](2026-09-08-capture.md)** | **~2026-09-08 · 지금 최우선** |
| 🟡 | [robosec](robosec/README.md) | 위협 모델·불변식 작성 완료. harness 미착수 |
| 📅 | systems-security-lab | 2026-09 착수 |
| 📅 | udp-network-lab | 2026-11 (자작 파서가 곧 이것) |
| 📅 | cryptography-lab | 보조 트랙 |

---

# 시간 예산 — 먼저 정직하게

2026-09 ~ 2027-02 = **26주 × 20시간 = 520시간.**

| 묶음 | 시간 |
|---|---|
| **로봇 마지막 10일 수집** (P2·P3) | **5** |
| 0주차 환경 구축 | 3 |
| CS:APP Ch1~3 + 15-213 슬라이드 | 40 |
| Data Lab · Bomb Lab · Attack Lab | 52 |
| OSTEP 핵심 10장 + homework | 45 |
| Shell Lab | 25 |
| Practical Binary Analysis (1·2·5·6·7장) | 30 |
| pwn.college — Reverse Engineering · ROP · 힙 | 50 |
| Security Engineering 6개 장 | 25 |
| SEED Labs 4개 | 25 |
| Sanitizer + 자작 패킷 파서 | 30 |
| libFuzzer + AFL++ | 50 |
| **RoboSec** | **100** |
| write-up · 저장소 정리 | 30 |
| **합계** | **510** |

여유 10시간(2%)입니다. **빡빡합니다.** 그래서 아래를 잘랐습니다.

## 잘라낸 것과 이유

| 뺀 것 | 이유 | 대체 |
|---|---|---|
| **Malloc Lab** (40h) | CS:APP 할당자는 glibc 와 구조가 다릅니다. 힙 익스플로잇에 필요한 tcache·fastbin·unlink 가 안 나옵니다 | Ch9.9 읽고 **pwn.college 힙 모듈** (C) |
| **Proxy Lab** (30h) | 이미 5G/UDP 와 Host↔Pi 링크를 만드셨습니다. 한계효용 최저 | 없음 |
| **Cache Lab** (15h) | 사이드채널로 갈 때만 필요 | SEv3 19장 읽는 것으로 대체 |
| **Architecture Lab** | 보안과 무관 | 없음 |
| SEv3 11장 → **6장** | 1,212쪽을 다 읽을 시간이 없습니다 | 아래 선별 |
| Cryptopals Set 3 이후 | 보조 트랙 | 2027-03 이후 |

**RoboSec 에 100시간을 배정한 것이 이 계획의 핵심입니다.** CS:APP·OSTEP·SEED 를
다 한 지원자는 많습니다. **자기가 만든 로봇의 위협 모델을 쓰고 실험한 지원자는
거의 없습니다.** 시간이 모자라면 앞쪽을 더 자르고 RoboSec 를 지키세요.

---

# 지금 — 로봇 마지막 10일 (~2026-09-08) 🔴

**환경 구축보다 먼저입니다.** Docker 는 다음 주에 깔아도 되지만, 로봇은
9월 8일이 지나면 없습니다.

| 우선 | 항목 | 비용 |
|---|---|---|
| P0 | 캡스톤 마무리 · 데모 (본 업무) | — |
| **P1** | **ros2 bag 녹화를 켜 두기** | **거의 0** |
| P2 | 하드웨어로만 잴 수 있는 상수 4개 | 4h |
| P3 | 포트폴리오 영상·사진 7종 | 1h |
| P4 | Host↔Pi 실기 통합 (팀 의존) | — |

전체 절차와 체크리스트 → **[`2026-09-08-capture.md`](2026-09-08-capture.md)**

> **시간이 모자라면 P1 과 P2-1(정지 지연 `T_stop`) 을 지키세요.** 이 둘이 없으면
> RoboSec 의 핵심 질문 두 개가 통째로 사라집니다.

---

# 0주차 — 환경 (3시간) · 2026-09-01 주

**이걸 먼저 하지 않으면 1주차에 막힙니다.** Bomb Lab 바이너리는 x86-64 Linux ELF
이고, 이 맥은 arm64 이며, **GDB 는 macOS 네이티브로 못 씁니다.**

| 할 일 | 환경 |
|---|---|
| Docker Desktop + Homebrew LLVM + binutils 설치 | A |
| Rosetta 가속 켜기, arm64/amd64 양쪽 확인 | A |
| `labs:amd64` 이미지 굽기 (gdb·gcc·binutils 포함) | B2 |
| ASan/UBSan 동작 확인 (이미 됨 — 검증 완료) | A |
| `$HOMEBREW_CLANG` 로 libFuzzer 링크 확인 | A |

명령 전문은 [`mac-environment.md` 0주차 설치](mac-environment.md#0주차-설치-약-1시간) 에 있습니다.

**산출물:** `systems-security-lab` 저장소 개설 + `00-environment/README.md` —
이 맥에서 무엇이 되고 무엇이 안 되는지 기록. **이것 자체가 첫 write-up 입니다.**

---

# 2026-09 — 기계어와 GDB

## 공부

| 항목 | 환경 | 시간 |
|---|---|---|
| CS:APP Ch1 + 15-213 Overview 슬라이드 | A | 6h |
| CS:APP Ch2 (정수·부동소수) + Bits/Bytes/Integers 슬라이드 | A | 14h |
| CS:APP Ch3 (기계어) + Machine Programming 슬라이드 | A | 20h |
| GDB cheat sheet (`gdbnotes-x86-64.pdf`) | — | 2h |

## 실습

### Data Lab (8h) · A

`~ & ^ | + << >>` 만으로 C 함수를 구현합니다. **for·if·조건연산자 금지, 연산자
개수 제한.** `btest`(정답) · `dlc`(규칙 위반) · `driver.pl`(점수) 로 자동 채점.

**맥에서 그대로 됩니다** — 순수 C 이고 아키텍처 의존이 없습니다.

> **왜 하나:** 2의 보수와 IEEE 754 가 "읽어서 아는 것"에서 "손에 붙은 것"이
> 됩니다. 나중에 UBSan 이 잡는 정수 오버플로가 왜 취약점인지 바로 보입니다.
> 중요도는 낮지만 **싸고 빠릅니다.**

### Bomb Lab (22h) · A + B2 ★

6단계 폭탄 바이너리를 역분석해 정답 문자열을 찾습니다. 소스는 없습니다.
단계별 주제: 문자열 비교 → 루프 → 스택/재귀 → 점프 테이블 → 연결 리스트.

**작업 방식 — 두 환경을 나눠 씁니다.**

```
objdump -d --no-show-raw-insn bomb > bomb.asm
```

이건 **맥에서 네이티브로 됩니다** (llvm-objdump 가 x86-64 를 읽습니다).
에디터에 `bomb.asm` 을 띄워 놓고 읽으세요. **실행과 GDB 만** 컨테이너로:

```
docker run --rm -it --platform linux/amd64 \
  --cap-add=SYS_PTRACE --security-opt seccomp=unconfined \
  -v "$PWD":/labs -w /labs labs:amd64
```

**기록 방식** — Phase 마다 세 짝:

```
02-x86-gdb/bomb-lab/phase_N/
├── disassembly.txt
├── analysis.md      ← 어떤 함수가 호출되나 · 인자는 어느 레지스터로 오나
│                       %rsp/%rbp 가 어떻게 변하나 · 조건 분기는 무엇을 검사하나
│                       breakpoint 를 어디 걸었나 · 가설을 GDB 로 어떻게 검증했나
└── gdb-session.txt
```

> ⚠️ **정답 문자열은 저장소에 올리지 않습니다.** Bomb Lab 은 매 학기 실제 수업에서
> 쓰입니다. 공개하는 것은 **분석 과정**이고, 정답과 배포 바이너리는 뺍니다.

## 이달의 산출물

- **로봇 수집 완료** — bag 파일 · 실측 상수 4종 · 영상/사진 7종 (~9/8)
- `systems-security-lab` 저장소 — `00-environment` · `01-c-and-memory` · `02-x86-gdb`
- Bomb Lab write-up 6개 Phase
- 포트폴리오 저장소에 **데모 GIF · 실측 사진** 추가 (grippers 문서 보강)

> 9월은 앞 10일이 로봇, 뒤 3주가 CS:APP 입니다. 로봇 수집이 밀리면
> **Bomb Lab 을 10월로 미루세요** — 순서를 바꿀 수 있는 쪽은 Bomb Lab 입니다.

---

# 2026-10 — 익스플로잇과 프로세스

## 실습

### Attack Lab (22h) · B2 ★

`ctarget` / `rtarget` 의 버퍼 오버플로를 실제로 익스플로잇합니다.
**코드 주입 3문제 + ROP 2문제.** 뒤 2문제는 NX·ASLR 때문에 주입이 안 되고,
바이너리 안의 gadget 을 이어 붙여야 합니다.

**여기가 로드맵 전체에서 가장 중요한 지점입니다.** "버퍼 오버플로가 위험하다"를
아는 것과 **직접 리턴 주소를 계산해 흐름을 뺏는 것**은 다릅니다.

write-up 에 넣을 것: vulnerability → stack layout → exploit reasoning →
GDB verification → ROP chain reasoning → **mitigation** → lessons learned.

### 같은 취약점을 arm64 로 다시 (6h) · A

Attack Lab 이 끝나면 **같은 개념의 자작 취약 프로그램을 두 아키텍처로** 만드세요.

```
clang -O0 -g -fno-stack-protector vuln.c -o vuln_arm64
docker run --rm --platform linux/amd64 -v "$PWD":/w -w /w gcc:13 \
  gcc -O0 -g -fno-stack-protector vuln.c -o vuln_amd64
```

스택 배치와 gadget 이 어떻게 달라지는지 비교한 write-up 은 흔치 않고,
**RoboSec 의 대상(Pi 5)이 aarch64 이므로 본론입니다.**

### Shell Lab (25h) · B2

`fork` / `execve` / `waitpid` / 시그널 핸들러로 유닉스 셸. 잡 컨트롤과
`SIGCHLD` 경쟁 조건.

> **왜 하나:** 시그널 경쟁 조건은 직접 당해 봐야 이해됩니다. 그리고 **fuzzer 가
> 자식 프로세스를 어떻게 띄우고 크래시를 어떻게 감지하는지**가 전부 이 지식
> 위에 있습니다 — 12월에 AFL++ 를 볼 때 회수됩니다.

## 공부

| 항목 | 환경 | 시간 |
|---|---|---|
| OSTEP — Processes · Process API · Address Spaces · Paging · TLB | A | 20h |
| OSTEP homework 시뮬레이터 (해당 장) | A | 8h |
| CS:APP Ch8(예외 제어 흐름) · Ch9(가상 메모리) | A | 12h |

### 가상 메모리 실습 (A)

C 프로그램에서 지역변수 · 전역변수 · static · `malloc` · 함수 주소를 출력하고,
`/proc/<pid>/maps` · lldb · `greadelf` · `objdump` 로 실제 배치와 잇습니다.

> **맥 주의:** macOS 에는 `/proc` 이 없습니다. **이 실습은 B1(arm64 컨테이너)에서**
> 하세요 — 네이티브 속도이고 `/proc` 이 있습니다.

## 이달의 산출물

- Attack Lab write-up (완화 기법 절 포함)
- **x86-64 vs aarch64 스택 비교** write-up ← 차별화 지점
- Shell Lab
- `04-memory-exploitation` 디렉터리

---

# 2026-11 — 바이너리 분석과 sanitizer

## 공부

| 항목 | 환경 | 시간 |
|---|---|---|
| Practical Binary Analysis 1·2·**5**·6장 (5장은 무료 공개) | B1 | 20h |
| OSTEP — Threads · Locks · Concurrency Bugs | A | 15h |
| **SEv3 1·2·4장** (What is SE · Who is the Opponent · Protocols) | A | 12h |

> SEv3 는 이미 `~/Desktop/포트폴리오/공부/SEv3.pdf` 에 있습니다 (1,212쪽).
> **6개 장만 읽습니다** — 선별 목록은 아래 별도 절에.

## 실습

### pwn.college — Reverse Engineering (25h) · C

브라우저에서 돕니다. **설치가 필요 없어서 이 맥에서 가장 마찰이 적은 실습**입니다.
Bomb Lab 이 끝난 직후가 최적 타이밍입니다.

### 자작 패킷 파서 + ASan/UBSan (30h) · A → B1

**로드맵 전체를 잇는 물건입니다.** 이 파서가 12월 fuzzing 대상이 되고,
`udp-network-lab` 의 본체가 되며, RoboSec 의 예행연습입니다.

```
[MAGIC][VERSION][SEQ][TIMESTAMP][TYPE][LENGTH][PAYLOAD][CHECKSUM]
```

> **필드 구성이 의도적입니다.** grippers 의 Host↔Pi 링크에는 **`SEQ` 와
> `TIMESTAMP` 가 없습니다.** 있는 버전을 직접 만들어 보면 그 부재가 무엇을
> 뜻하는지 몸으로 압니다 — 그것이 RoboSec 위협 모델의 A3(replay) 입니다.

학습용 버그를 의도적으로 심습니다: out-of-bounds read/write · malformed length ·
정수 오버플로 · use-after-free · invalid enum · 검증 누락.

ASan/UBSan 은 **맥 네이티브에서 그대로 됩니다** (검증 완료):

```
clang -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer \
  parser.c test_main.c -o parser_san
```

커밋 이력을 이렇게 남기세요 — **이력 자체가 방법론의 증거입니다:**

```
1  implement minimal packet parser
2  add malformed-input regression tests
3  reproduce bounds violation with ASan
4  fix length validation
5  add regression test
```

> ⚠️ 취약한 버전을 남길 때는 **파일 안에 명시**하세요:
> `/* 학습용 취약 코드 — 의도적으로 경계 검사 없음. 고친 버전은 fix.c */`

## 이달의 산출물

- ELF 분석 · lldb/GDB write-up
- **sanitizer 리포트** — 버그별 재현 → 원인 → 수정 → 회귀 테스트
- 파서 회귀 테스트 스위트

---

# 2026-12 — Fuzzing

**여기서 단순 튜토리얼이 작은 실험 프로젝트로 바뀝니다.**

## Step 1 — libFuzzer (25h) · A + B1

> ⚠️ **Apple clang 으로는 안 됩니다.** `libclang_rt.fuzzer_osx.a` 가 없습니다
> (실측 확인). Homebrew clang 을 쓰세요.

```
$HOMEBREW_CLANG -g -O1 -fsanitize=fuzzer,address,undefined \
  fuzz_target.c parser.c -o fuzz_target
mkdir -p corpus && ./fuzz_target corpus
```

기록할 것: corpus · coverage · executions · 발견한 크래시 · **최소화된 입력** ·
스택 트레이스 · 근본 원인 · 패치 · 회귀 테스트.

## Step 2 — AFL++ (25h) · B1 ★

**반드시 `linux/arm64` 컨테이너에서** 하세요. amd64 로 하면 Rosetta 에뮬레이션이라
느리고, **측정값이 네이티브와 비교 불가**해집니다.

```
docker run --rm -it --platform linux/arm64 \
  -v "$PWD":/src -w /src aflplusplus/aflplusplus
```

같은 파서를 두 도구로 돌리고 **실측값만** 비교합니다:

| 지표 | libFuzzer | AFL++ |
|---|---|---|
| executions/sec | 측정 | 측정 |
| coverage | 측정 | 측정 |
| time-to-first-crash | 측정 | 측정 |
| corpus size | 측정 | 측정 |
| unique failures | 측정 | 측정 |

> **표에 반드시 환경을 명기하세요** — "linux/arm64 컨테이너 · M1 Pro · 8 성능코어".
> 환경 없는 fuzzing 수치는 아무 의미가 없습니다.

**`afl-fuzz` 화면 캡처는 포트폴리오 가치가 거의 없습니다.** 가치는
`크래시 → ASan 스택 트레이스 → 디버거 → 근본 원인 → 패치 → 회귀 테스트` 전체
사이클에 있습니다.

## Step 3 — 힙 (10h) · C

pwn.college **Dynamic Allocator Misuse.** Malloc Lab 40시간을 여기 10시간으로
대체합니다 — glibc 의 tcache·fastbin 이 실제로 익스플로잇에 쓰이는 것입니다.

## 이달의 산출물

- **fuzzing 리포트** — libFuzzer vs AFL++ 실측 비교 (환경 명기)
- 재현 가능한 실험 스크립트
- `udp-network-lab` 저장소 개설 (파서가 이미 실체입니다)

---

# 2027-01 — 보안 아키텍처와 RoboSec 착수

## 공부 — SEv3 선별 6개 장 (25h) · A

1,212쪽을 다 읽지 않습니다. **이 순서로 6개만:**

| 장 | 제목 | 쪽 | 왜 |
|---|---|---|---|
| 1 | What Is Security Engineering? | 3 | 프레임 |
| 2 | Who Is the Opponent? | 17 | **위협 모델의 원전** |
| 4 | Protocols | 119 | Host↔Pi 링크가 곧 프로토콜 |
| 6 | Access Control | 207 | "누가 명령을 낼 수 있나" |
| 7 | Distributed Systems | 243 | 2대로 나뉜 시스템 |
| **28.4** | **The entanglement of safety and security** | **1044** | ★ **이 절이 핵심** |

> **§28.4 를 놓치지 마세요.** safety 와 security 가 얽히는 지점을 다루는 절이고,
> §28.4.1 은 자동차의 전자적 safety/security 를 봅니다 — **RoboSec 의 논지가
> 바로 여기서 나옵니다.** (참고: 13장은 "Locks and Alarms" 로 물리 자물쇠 이야기라
> 관련이 없습니다.)
>
> 여유가 생기면 §27.3 Lessons from safety-critical systems (969쪽) 과
> §25.2 Autonomous and remotely-piloted vehicles (866쪽) 를 추가하세요.

각 장을 읽고 **grippers 에 적용해 질문**합니다 — 이것이 위협 모델을 두껍게 합니다.

| 장 | 질문 |
|---|---|
| Protocols | Pi 는 command packet 이 진짜 Host 에서 왔다는 것을 어떻게 확인하는가? |
| Access Control | Host 만 actuator command 를 만들 수 있다는 것을 무엇이 보장하는가? |
| Distributed | packet loss 나 service delay 가 safety property 를 깨뜨릴 수 있는가? |
| §28.4 | safety 층(속도 클램프)과 security 층은 같은 것인가 다른 것인가? |

## 실습 — SEED Labs 4개 (25h) · B2

40개가 넘지만 **4개만** 합니다. 순서와 이유:

1. **Buffer Overflow** — Attack Lab 의 복습이자 리눅스 실환경 버전
2. **Race Condition** — Shell Lab 의 시그널 경쟁과 이어짐
3. **Packet Sniffing / Spoofing** — ★ **RoboSec A2(스푸핑)의 직접 예행연습**
4. **TCP Attacks** — 재전송·재정렬의 감각

> **맥 주의:** SEED Labs 는 대부분 x86 전제라 **B2(amd64 컨테이너)** 가 필요합니다.
> arm64 셋업이 제공되는 랩도 일부 있으니 랩별로 확인하세요. 3번 Sniffing/Spoofing
> 은 컨테이너 네트워크 권한(`--cap-add=NET_ADMIN`)이 필요합니다.

## RoboSec 착수 (30h) · A

**위협 모델과 불변식은 이미 작성돼 있습니다** ([`robosec/`](robosec/)).
이달에는 그 위에 harness 를 올립니다.

| 할 일 | 환경 |
|---|---|
| 위협 모델 재검토 — SEv3 4·6·7장 읽은 뒤 보강 | A |
| `stop` 필드 처리 경로 코드 대조 (지금 미확인) | A |
| 프로토콜 독립 구현 (`protocol/`) — Pi 코드를 import 하지 않고 규격에서 다시 | A |
| harness 설계 — SUT 를 띄우고 불변식 I1~I8 을 관측하는 층 | A |
| `domain/task/motion.py` · `baseline_mission.py` 를 대상으로 첫 fuzzing | A |
| **녹화본 replay harness** — bag 을 읽어 명령 시퀀스를 재생 | A |

> **핵심: 로봇은 이미 없습니다. 그래도 됩니다.** 도메인 코드가 순수 파이썬이고
> ROS 도 하드웨어도 모르게 설계돼 있어서 **맥에서 그대로 fuzzing 됩니다.**
> 이건 grippers 를 Ports & Adapters 로 만든 것의 배당금입니다.
>
> 9월에 확보한 bag 이 **모델의 정답지** 역할을 합니다 — 모델이 녹화된 궤적을
> 재현하는지 먼저 보이고, 그다음에 모델 위에서 탐색합니다.

## 이달의 산출물

- `threat_model.md` v2 · `security_properties.md` v2
- `protocol/` 독립 구현
- 첫 harness + 첫 불변식 위반 (있다면)

---

# 2027-02 — RoboSec 실험과 리포트

## 실험 (60h) · **전부 A** — 로봇은 없습니다

**모든 실험이 맥에서 돕니다.** 물리적 결과가 필요한 자리는 9월에 확보한 실측값과
녹화본으로 대체합니다.

| 실험 | 질문 | 물리 근거 |
|---|---|---|
| E1 | 손상 페이로드를 다량 주입하면 정상 명령의 실효 수신율은? | 불필요 — 순수 소프트웨어 |
| E2 | 유효 형식 명령을 자주 주입하면 — 클램프는 크기만 자르는데 **방향**은? | 9월 통주행 bag 의 정상 궤적과 대조 |
| E3 | 이전 GRASP 명령을 재전송하면 상태 게이팅이 막는가? | 불필요 — FSM 로직 |
| E4 | 링크 침묵 시 워치독 발동까지 몇 초, 그동안 몇 mm? | **P2-2 실측값 고정** |
| E5 | stop 명령의 오버슈트가 INSERT 허용창(±15 mm)보다 큰가? | **P2-1 실측 `T_stop`** |

> **E4·E5 는 9월에 값을 못 재면 쓸 수 없습니다.**
> → [`2026-09-08-capture.md`](2026-09-08-capture.md) P2-1 · P2-2

### 모델 검증을 먼저 합니다

탐색 전에 **모델이 실물을 얼마나 재현하는지**를 보여야 결과에 값이 생깁니다.

1. 9월 bag 에서 명령 시퀀스를 뽑아 도메인 코드에 재생
2. 모델이 낸 `/cmd_vel` 과 녹화된 `/cmd_vel` 을 비교 — 일치율을 수치로
3. 그 위에서 fuzzing 탐색

이 절차가 리포트의 **Experimental Setup** 절이 됩니다.

## Technical Report (30h)

5~8쪽. **README 보다 리포트가 대학원 포트폴리오에서 중요합니다.**

```
1. Introduction          6. Experimental Setup
2. Background / 시스템 구조  7. Results
3. Threat Model          8. Discussion
4. Security/Safety Properties  9. Limitations
5. Testing Method        10. Future Work
```

측정 지표: 생성 입력 수 · 상태 전이 커버리지 · 고유 실패 수 ·
**불변식 위반 수(I1~I8 각각)** · 최초 위반까지의 시간 · crash 수(참고).

**Limitations 에 반드시 들어갈 문장:**

> Physical validation was performed on N recorded runs before hardware access
> ended on 2026-09-08. Subsequent exploration is model-based, using the
> hardware-independent domain layer as the system under test, with recorded
> traces as ground truth.

**모델 기반 탐색 + 제한된 물리 검증**은 사이버-물리 시스템 보안 연구의 표준
구성입니다. 약점이 아니라 방법론이며, 중요한 것은 ① 모델이 실측과 얼마나
맞는지 보이는 것과 ② 검증하지 못한 것을 정확히 밝히는 것뿐입니다.

## 이달의 산출물

- `robosec` 저장소 분리 · 공개
- 재현 가능한 실험 스크립트 · 결과 표/그림
- **technical report v1**
- CV 의 RoboSec 항목에 **정량 결과** 추가

---

# 주간 루틴 (주 20시간)

| 시간 | 항목 |
|---|---|
| 6h | CS:APP / OSTEP |
| 6h | Lab / 실습 |
| 3h | Security Engineering / 논문 |
| 3h | grippers / RoboSec |
| 2h | write-up · 저장소 정리 |

시간이 부족하면 비율을 유지하며 전체를 줄입니다.

> **공부 : 실습 ≥ 1 : 1**
>
> 그리고 **write-up 2시간을 먼저 자르지 마세요.** 기록하지 않은 실습은 3개월 뒤에
> 안 한 것과 같아집니다.

---

# 실습 기록 4원칙

모든 실습에 네 가지를 남깁니다. 틀은 [`../templates/WRITEUP_TEMPLATE.md`](../templates/WRITEUP_TEMPLATE.md).

1. **What I learned** — 무슨 개념을 배웠나
2. **What I built** — 직접 무엇을 만들거나 분석했나
3. **What failed** — 무엇이 예상과 다르게 동작했나 *(비어 있으면 실습을 안 한 것입니다)*
4. **How I verified it** — 어떤 도구와 측정으로 확인했나

여기에 이 맥 특유의 다섯 번째를 더합니다.

5. **Which environment** — A / B1 / B2 / C / D 중 어디서 돌렸나.
   **성능 수치에는 반드시 명기합니다.**

---

# 앞으로 만들 저장소

지금 만들지 않는 이유는 하나입니다 — **빈 저장소가 여러 개 떠 있는 것이 하나도
없는 것보다 나쁩니다.** 내용이 생긴 달에 만듭니다.

| 저장소 | 개설 시점 | 첫 내용 |
|---|---|---|
| `systems-security-lab` | **2026-09** | `00-environment` — 이 맥에서 무엇이 되고 안 되는지 |
| `udp-network-lab` | 2026-12 | 자작 패킷 파서 + fuzzing 리포트 |
| `robosec` | 2027-02 | 위협 모델 + 실험 결과 + 리포트 |
| `cryptography-lab` | 2027-03 이후 | Cryptopals Set 1~2 |

## 공개 정책 — 먼저 정해 둡니다

**공식 lab 의 정답이나 exploit 페이로드는 공개하지 않습니다.** CMU 15-213 의
Bomb/Attack Lab 은 매 학기 실제 수업에서 쓰입니다.

| 공개 | 비공개 |
|---|---|
| 분석 과정 · GDB 사용법 · 가설 검증 | 정답 문자열 · 완성된 페이로드 |
| **직접 만든 취약 프로그램** | 배포된 바이너리 |
| 완화 기법 적용 전후 비교 | 공식 solution 파일 |

**자작 취약 프로그램으로 재현하는 쪽이 포트폴리오로도 낫습니다** — "주어진 문제를
풀었다"보다 "같은 취약점을 스스로 만들고 관찰하고 고쳤다"가 더 많은 것을
보여줍니다.

---

# 두 갈래의 표현 차이

기술 기반은 하나이고, 마지막 표현만 다릅니다.

| | 대학원 | 취업 |
|---|---|---|
| 핵심 질문 | **Why?** | **How?** |
| 강조 | 연구 문제 · 방법 · 실험 | 구현 · 디버깅 · 검증 |
| grippers | research testbed | 대표 시스템 |
| RoboSec | 대표 연구 프로젝트 | Reliability/Security 프로젝트 |
| Technical report | 중요 | 선택 |
| README · 측정 결과 | 중요 | **매우 중요** |

- **대학원:** Research Question → Method → Experiment → Result
- **취업:** Problem → Implementation → Debugging → Verification → Result

---

# 이 계획이 깨질 때

6개월 계획은 반드시 밀립니다. **밀릴 때 무엇을 버릴지 미리 정해 둡니다.**

| 우선순위 | 버리지 않는 것 |
|---|---|
| 0 | **로봇 마지막 10일 수집 (~9/8)** — 놓치면 되돌릴 수 없음 |
| 1 | **RoboSec 실험과 리포트** — 유일한 차별화 지점 |
| 2 | Bomb Lab · Attack Lab — 나머지 전부의 전제 |
| 3 | 자작 파서 + sanitizer + fuzzing 한 사이클 |
| 4 | SEv3 2장 · 4장 · **§28.4** |
| — | *이 아래는 전부 버려도 됩니다* |
| 5 | Shell Lab · OSTEP 동시성 · SEED Labs · pwn.college · Cryptopals |

**5번을 다 하고 1번을 못 하면 이 6개월은 실패입니다.**
