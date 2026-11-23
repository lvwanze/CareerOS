"""测试公共配置（结构无关）：后端发现 + fixtures + 依赖目录自定位。

设计目标：tests/ 内部无论怎么组织，测试都能跑——
  * 扁平结构：所有 test_*.py / factories.py / reference/ 直接放在 tests/ 下
  * 分类结构：测试放"自动化测试代码文件/"，支撑放"公共支撑文件/"，reference 单独
  * 或任何自定义子目录
切换时只需移动文件，本文件与测试代码都不用改。

三条机制保证结构无关：
  1. 本 conftest 固定在 tests/ 根目录——pytest 的 fixture 对所在目录及
     所有递归子目录可见，因此 fixture 全局可用（放子目录则只对兄弟目录失效）。
  2. 递归查找 factories.py 与 reference 包，把它们的父目录加入 sys.path，
     使 `from factories import ...` / `from reference.xxx import ...` 永远能解析。
  3. 数据交付包由 reference/real_data.py 向上逐级查找（支持 CAREEROS_DATASET_ROOT）。

接入真实后端（二选一）：
  * 把代旭的 FastAPI 仓库放到项目根/careeros/；或
  * 设置环境变量 CAREEROS_ROOT=<后端仓库绝对路径>。
检测到真实 app 后，接口/端到端用例自动切换到真实实现；
若接口路径与契约不同，设置 CAREEROS_RECOMMEND_PATH=/实际路径。
"""

import importlib
import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

TESTS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TESTS_DIR.parent


def _add_syspath(path: Path):
    """把目录加入 sys.path（去重、只加存在的目录）。"""
    if path.is_dir() and str(path) not in sys.path:
        sys.path.insert(0, str(path))


def _locate_module(name: str):
    """在 tests/ 树下递归定位模块，返回需要加入 sys.path 的目录。

    name.py        → 返回该文件所在目录
    name/__init__.py → 返回包的父目录（这样 `import name` 才成立）
    找不到时返回 None。
    """
    for path in TESTS_DIR.rglob(f"{name}.py"):
        return path.parent
    for path in TESTS_DIR.rglob(f"{name}{os.sep}__init__.py"):
        return path.parent.parent
    return None


# 基础路径：测试根 + 项目根（无论结构如何都加）
_add_syspath(TESTS_DIR)
_add_syspath(PROJECT_ROOT)

# 递归定位依赖：factories.py（测试样本）与 reference 包（契约模型/参考实现）
for _dep in ("factories", "reference"):
    _dir = _locate_module(_dep)
    if _dir is None:
        raise RuntimeError(
            f"[CareerOS 测试] 在 tests/ 树下未找到依赖 '{_dep}'，"
            "请确认 factories.py 与 reference/ 随测试包一起交付。"
        )
    _add_syspath(_dir)

API_RECOMMEND_PATH = os.environ.get(
    "CAREEROS_RECOMMEND_PATH", "/api/v1/recommendations"
)


def _discover_backend_root():
    env_root = os.environ.get("CAREEROS_ROOT")
    if env_root:
        return Path(env_root).expanduser()
    guess = PROJECT_ROOT / "careeros"
    if guess.is_dir():
        return guess
    # 仓库布局：本测试位于 <backend>/tests/acceptance/ 时，向上找含
    # packages/service 的 backend 根，clone 后无需任何环境变量即可接真实后端。
    for base in [TESTS_DIR] + list(TESTS_DIR.parents)[:6]:
        if (base / "packages" / "service").is_dir():
            return base
    return None


BACKEND_ROOT = _discover_backend_root()
if BACKEND_ROOT and str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

REAL_APP = None
REAL_APP_MODULE = None
if BACKEND_ROOT is not None:
    for _module_name in (
        "app.main",
        "packages.service.main",
        "service.main",
        "service.app",
        "api.main",
        "main",
    ):
        try:
            _module = importlib.import_module(_module_name)
        except Exception:
            continue
        _candidate = getattr(_module, "app", None)
        if _candidate is not None and hasattr(_candidate, "routes"):
            REAL_APP = _candidate
            REAL_APP_MODULE = _module_name
            break


def pytest_configure(config):
    for name, desc in (
        ("contract", "数据契约与字段校验"),
        ("api", "接口测试"),
        ("algorithm", "算法输入输出测试"),
        ("recommendation", "推荐与技能差距测试"),
        ("e2e", "端到端链路测试"),
        ("exception", "异常与边界测试"),
        ("data_version", "数据版本与完整性校验（FR-09）"),
        ("name_mapping", "中英名称参考映射校验（派生参考数据，非契约三表）"),
    ):
        config.addinivalue_line("markers", f"{name}: {desc}")

    reporter = config.pluginmanager.getplugin("terminalreporter")
    if reporter is not None:
        if REAL_APP is not None:
            reporter.write_line(
                f"[CareerOS 测试] 接口来源：真实后端 {REAL_APP_MODULE}", green=True
            )
        else:
            reporter.write_line(
                "[CareerOS 测试] 接口来源：参考 stub（自检模式）"
                "—— 不代表真实系统已通过测试",
                yellow=True,
            )


@pytest.fixture(scope="session")
def api_mode():
    return "real" if REAL_APP is not None else "stub"


@pytest.fixture(scope="session")
def recommend_path():
    return API_RECOMMEND_PATH


@pytest.fixture(scope="session")
def app_under_test():
    if REAL_APP is not None:
        return REAL_APP
    from reference.stub_app import app

    return app


@pytest.fixture(scope="session")
def client(app_under_test):
    with TestClient(app_under_test) as test_client:
        yield test_client
