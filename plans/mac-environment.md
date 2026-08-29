# 실습 환경 — Apple Silicon 맥 기준

> **2026-08-29 이 맥에서 직접 실행해 확인한 결과입니다.** 추정이 아닙니다.
> 로드맵의 모든 작업에는 아래 A/B1/B2/C/D 중 어디서 도는지가 표시돼 있습니다.

---

## 이 맥

```
Apple M1 Pro · 10코어 (성능 8 / 효율 2) · 메모리 16 GB · 디스크 여유 779 GB
macOS 15.7.7 (arm64) · Apple clang 17.0.0 · Homebrew 6.0.20
```

---

## 검증 결과

| 도구 | 맥 네이티브 | 근거 |
|---|---|---|
| **ASan** (`-fsanitize=address`) | ✅ **동작** | heap-buffer-overflow 실제 검출 확인 |
| **UBSan** (`-fsanitize=undefined`) | ✅ **동작** | signed overflow 실제 검출 확인 |
| **libFuzzer** (`-fsanitize=fuzzer`) | ❌ **불가** | `libclang_rt.fuzzer_osx.a` 없음 — Apple clang 에 런타임 미포함 |
| **GDB** | ❌ **불가** | 미설치. Apple Silicon macOS 타깃 지원 안 됨 |
| **lldb** | ✅ 있음 | arm64 네이티브 프로그램 디버깅용 |
| **objdump** (llvm) | ✅ **x86-64 읽음** | 등록 타깃에 `x86-64`, `aarch64` 모두 포함 |
| `readelf` | ❌ 없음 | `brew install binutils` → `greadelf`, 또는 컨테이너 |
| Docker / colima / UTM / qemu | ❌ 전부 미설치 | 설치 필요 |
| Rosetta | ✅ 실행 중 | amd64 컨테이너 가속에 사용 |

### 여기서 나오는 두 가지 결론

**1. GDB 작업은 전부 컨테이너 안에서 합니다.**
불편처럼 보이지만 실제로는 문제가 없습니다 — Bomb Lab · Attack Lab 바이너리가
어차피 **x86-64 Linux ELF** 라서 컨테이너에 들어가야 하기 때문입니다. 맥에서
GDB를 억지로 살리려 하지 마세요. 시간만 씁니다.

**2. 디스어셈블은 맥에서 네이티브로 됩니다.**
`objdump` 가 x86-64 타깃을 지원하므로 **바이너리를 읽는 일은 컨테이너 밖에서**
할 수 있습니다. 실행과 디버깅만 안으로 들어갑니다.

```
objdump -d --no-show-raw-insn bomb > bomb.asm
```

에디터에서 `bomb.asm` 을 열어 놓고, GDB 세션만 컨테이너에서 — 이 조합이 가장
편합니다.

---

## 다섯 개의 실행 환경

| | 환경 | 무엇을 하나 | 속도 |
|---|---|---|---|
| **A** | **맥 네이티브 (arm64)** | 읽기 · ASan/UBSan · 자작 취약 C · 정적 디스어셈블 · Cryptopals · RoboSec 도메인 코드 · lldb | 가장 빠름 |
| **B1** | **linux/arm64 컨테이너** | 자작 파서 fuzzing · AFL++ · libFuzzer · GNU binutils | **네이티브 속도** |
| **B2** | **linux/amd64 컨테이너** (Rosetta) | Bomb Lab · Attack Lab · SEED Labs · GDB | 에뮬레이션, 느림 |
| **C** | **브라우저** | pwn.college | 설치 불필요 |
| **D** | **라즈베리파이 5** (arm64 Linux) | 데이터 수집 — ⚠️ **2026-09-08 종료** | 실기 |

### B1 과 B2 를 구별하는 것이 핵심입니다

M1 맥에서 Docker 의 **기본 플랫폼은 `linux/arm64`** 이고, 이건 **에뮬레이션이
아니라 네이티브**입니다. `linux/amd64` 만 Rosetta 를 거칩니다.

그러니:

- **CMU 랩과 SEED Labs 만** amd64 (x86-64 바이너리라 선택지 없음)
- **내가 만든 코드를 fuzzing 할 때는 arm64** — 에뮬레이션 없이 전속력

> ⚠️ **측정값을 쓸 때 반드시 구별하세요.** amd64 컨테이너에서 잰
> `executions/sec` 은 Rosetta 위의 값이라 네이티브 x86-64 수치와 비교할 수
> 없습니다. fuzzing 벤치마크는 **B1(arm64)에서 재고, 어느 환경인지 명시**해야
> 합니다. 이 저장소의 "측정하지 않은 숫자는 쓰지 않는다" 규칙은 **어떻게
> 측정했는지 밝히는 것**까지 포함합니다.

---

## 아키텍처 비대칭 — 단점이 아니라 기회

| | 명령어 집합 |
|---|---|
| CS:APP 랩 · SEED Labs · 대부분의 익스플로잇 교재 | **x86-64** |
| 이 맥 · 라즈베리파이 5 · grippers 실기 | **aarch64** |

배우는 것과 만드는 것의 아키텍처가 다릅니다. 두 가지 대응이 있습니다.

**하나 — 교재는 x86-64 그대로 갑니다.** 자료가 압도적으로 많고, 스택 프레임 ·
호출 규약 · ROP 의 **개념은 이식됩니다.** 처음부터 arm64 자료를 찾아 헤매지
마세요.

**둘 — 자작 취약 프로그램은 두 아키텍처로 다 만듭니다.** 이건 비용이 거의 없고
(같은 C 소스를 `-target` 만 바꿔 컴파일) **얻는 것이 큽니다.**

```
clang -O0 -g -fno-stack-protector vulnerable.c -o vuln_arm64
docker run --rm --platform linux/amd64 -v "$PWD":/w -w /w gcc:13 \
  gcc -O0 -g -fno-stack-protector vulnerable.c -o vuln_amd64
```

같은 취약점이 두 아키텍처에서 **스택 배치와 gadget 이 어떻게 달라지는지** 쓴
write-up 은 흔치 않습니다. 그리고 RoboSec 의 대상인 Pi 가 aarch64 이므로
**이건 부수입이 아니라 본론**입니다.

---

## 0주차 설치 (약 1시간)

```
brew install --cask docker
brew install llvm binutils
```

Docker Desktop 을 실행하고 **Settings → General → Use Rosetta for x86/amd64
emulation** 을 켜세요. 그다음 두 플랫폼을 모두 확인합니다.

```
docker run --rm --platform linux/arm64 ubuntu:22.04 uname -m
docker run --rm --platform linux/amd64 ubuntu:22.04 uname -m
```

`aarch64` 와 `x86_64` 가 각각 나오면 준비 완료입니다.

libFuzzer 는 Homebrew clang 을 씁니다. Apple clang 이 아닙니다.

```
/opt/homebrew/opt/llvm/bin/clang --version
```

셸 설정에 넣어 두면 편합니다.

```
echo 'export HOMEBREW_CLANG=/opt/homebrew/opt/llvm/bin/clang' >> ~/.zshrc
```

### 실습용 amd64 이미지 하나 만들어 두기

Bomb/Attack Lab 을 할 때마다 도구를 다시 깔지 않도록 이미지를 하나 굽습니다.
`~/labs/Dockerfile` 로 저장하세요.

```
FROM --platform=linux/amd64 ubuntu:22.04
RUN apt-get update && apt-get install -y \
    gdb gcc make binutils vim python3 python3-pip file strace ltrace \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /labs
```

```
cd ~/labs
docker build -t labs:amd64 .
docker run --rm -it --platform linux/amd64 -v "$PWD":/labs labs:amd64
```

컨테이너 안에서 GDB 가 돕니다. 파일은 맥과 공유되므로 **에디터는 맥에서, 실행은
컨테이너에서** 쓰시면 됩니다.

---

## 자주 막히는 곳

| 증상 | 원인 | 해결 |
|---|---|---|
| `libclang_rt.fuzzer_osx.a not found` | Apple clang 에 libFuzzer 없음 | `$HOMEBREW_CLANG` 사용 |
| `exec format error` | arm64 에서 x86-64 ELF 실행 | `--platform linux/amd64` |
| `gdb: command not found` (맥) | 네이티브 GDB 불가 | 컨테이너 안에서 |
| `readelf: command not found` | binutils 없음 | `greadelf` 또는 컨테이너 |
| fuzzing 이 유난히 느림 | amd64 컨테이너에서 돌리는 중 | 자작 코드는 **B1(arm64)** 에서 |
| GDB 가 컨테이너에서 권한 오류 | ptrace 제한 | `--cap-add=SYS_PTRACE --security-opt seccomp=unconfined` |

---

## 라즈베리파이 5 — 2026-09-08 까지만

> 🔴 **하드웨어 접근이 2026-09-08 에 끝납니다.** 그 뒤로 D 환경은 존재하지
> 않습니다. 남은 기간에 확보할 것은
> [`2026-09-08-capture.md`](2026-09-08-capture.md) 에 있습니다.

그때까지는 Pi 가 **데이터 수집 대상**입니다. 이미 갖고 계신 arm64 Linux 실기라는
것이 큰 이점입니다 — 대부분의 학생은 이런 대상이 없어 문헌의 예제를 씁니다.
그 이점을 **녹화본의 형태로 남기는 것**이 남은 10일의 목표입니다.

**9월 8일 이후에도 RoboSec 는 계속됩니다.** 검사 대상인 도메인 코드
(`motion.py` · `baseline_mission.py` · `udp_host_link.py`)가 순수 파이썬이고
하드웨어를 모르기 때문에 **A 환경에서 그대로 돕니다.** 물리적 결과가 필요한
자리만 녹화본과 실측 상수로 대체합니다.

로봇을 쓰는 동안에는 **운용 규칙과 충돌하지 않게** 하세요.

- 실험은 **격리된 실험망**에서만. 외부 망에 붙은 상태로 주입 실험을 하지 않습니다
- 캘리브레이션 파일(`host/calib/*.npz`)은 **어떤 경우에도 건드리지 않습니다**
- 실험 후 `perception_node` 를 반드시 되살립니다
- 모든 셸에서 `ROS_DOMAIN_ID=21` 을 가장 먼저 export 합니다
- **차량이 움직일 수 있는 실험은 바퀴를 띄우거나 팔을 분리한 상태에서** 먼저
  합니다. 속도 클램프를 시험하는 실험이 클램프가 깨진 상태에서 돌면 로봇이 실제로
  튀어나갑니다

파이썬 도메인 코드(`domain/task/motion.py`, `baseline_mission.py`)는
**하드웨어 없이 맥에서(A) 그대로 fuzzing 할 수 있습니다.** 이것이 9월 8일 이후에도
RoboSec 가 성립하는 이유이고, grippers 를 Ports & Adapters 로 만든 것의
배당금입니다.
