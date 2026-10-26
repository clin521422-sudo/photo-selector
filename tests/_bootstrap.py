"""测试公共引导：把项目根目录加入 sys.path，方便 tests/ 下直接跑。"""

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SAMPLES = ROOT / "samples"
