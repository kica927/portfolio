# AFL++ 퍼징 — sf_decode (리눅스 데스크탑)

libFuzzer 로 이미 검증한 `sf_decode` 를 **AFL++ 로 한 번 더** 돌려 커버리지·발견을
비교한다. 두 퍼저는 탐색 전략이 달라(coverage-guided libFuzzer vs. AFL++ 의
edge 계측·havoc 변이), 같은 대상을 두 도구로 보면 사각을 줄일 수 있다.

## 왜 여기(리눅스)서만

맥(Apple Silicon)은 `afl-clang-fast` 의 LLVM 계측 설치가 까다롭다. 그래서
libFuzzer 는 맥에서 돌리고(`../fuzz_decode.c`, 1,300만 회 크래시 0),
AFL++ 는 계측이 매끄러운 **리눅스 데스크탑**(Arc B580 머신)에서 돌린다.

## 실행

```
sudo apt install afl++ clang libssl-dev python3   # 선행
bash run_afl.sh                                    # Ctrl-C 로 종료
```

- `afl_harness.c` — AFL++ persistent-mode 하네스. libFuzzer 하네스와 **같은
  진입점(`sf_decode`)** 을 겨눈다.
- `make_seeds.py` — Python 레퍼런스로 유효/경계 프레임을 `seeds/` 에 바이너리로
  생성(유효 시드가 있어야 퍼저가 HMAC·CRC·길이 구조를 빨리 학습한다).
- 결과는 `out/` — `out/default/crashes/` 가 비어 있어야 정상(무결점).

## 상태 (정직하게)

- 하네스·러너·시드 생성기 **준비 완료**.
- **AFL++ 실제 실행·커버리지 비교는 아직 안 했다** — 리눅스 데스크탑에서 수행
  예정. 로드맵의 *"AFL++ 는 실제로 쓴 뒤에 올린다"* 원칙에 따라, 실행 결과가
  나오면 이 문서에 실행 시간·경로 수·커버리지 대비를 기록한다.
