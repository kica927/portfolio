"""grippers 도메인 계층을 하드웨어 없이 부르기 위한 경로 설정.

grippers 저장소는 **읽기 전용으로 import 만** 한다 — 이 하네스는 grippers 에
파일을 쓰지 않고, PYTHONPATH 에 얹기만 한다. 저장소 경로가 다르면
GRIPPERS_ROOT 환경변수로 넘긴다.
"""

import os
import sys

# grippers 를 import 해도 그 트리에 .pyc 를 남기지 않는다 — 저장소를
# 건드리지 않기 위해서다.
sys.dont_write_bytecode = True

_DEFAULT = os.path.expanduser("~/Desktop/intel/grippers")
GRIPPERS_ROOT = os.environ.get("GRIPPERS_ROOT", _DEFAULT)

if GRIPPERS_ROOT not in sys.path:
    sys.path.insert(0, GRIPPERS_ROOT)

if not os.path.isdir(os.path.join(GRIPPERS_ROOT, "domain")):
    raise RuntimeError(
        f"grippers 도메인 계층을 못 찾음: {GRIPPERS_ROOT}. "
        "GRIPPERS_ROOT 환경변수로 저장소 경로를 지정하세요.")
