"""架构约束的显式放行清单（baseline allowlist）。

设计（清单 M5 P1「架构测试」）：
    架构测试扫描生产代码，检出违反分层/路径规范的越界；与本清单比对后：
      * 越界在清单内（已登记、有理由、有归属）→ 放行，不算违规；
      * 越界不在清单内（新引入）            → 构建失败。
    这样既让架构测试"进入 CI 且违反时构建失败"，又不把他人存量的、已有
    决策依据的现状判红——M5 不越界修改生产代码是本项目一贯边界。

每条放行项记录四要素：位置、约束、理由、依据/归属。删除或整改越界后，
应同步删除对应放行项；架构测试会在放行项"已不存在"时提示清理基线。

归属：M5 薛宏博（测试与质量）。依据：方案 A1「架构测试」、
《CareerOS 答辩验收清单》6.3 M5 P1。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Allowance:
    rule: str          # 约束名，与 test_*.py 中的 RULE 常量一致
    target: str        # 越界对象：模块导入路径 或 文件:行特征
    reason: str        # 为什么放行
    basis: str         # 依据（ADR 编号 / 清单条目 / 负责人）


# ---------------------------------------------------------------------------
# 约束 1：service 不依赖 training
# ---------------------------------------------------------------------------
# docs/decisions.md ADR-009「工程模块边界」要求：
#   "service 不直接调用 training 的训练脚本或训练入口。"
# recommend.py 导入的是 training.inference.generate_recommendations（**推理**入口，
# 非训练脚本/训练入口），按 ADR-009 字面不在禁止之列；README:335 亦写明
# "service 调用算法"属业务允许。新清单 5.2 指出这与方案 A1「api 只依赖 core」
# 存在口径冲突，须由 M3 代旭补专门 ADR 或收敛数据入口后再收紧。
# 故此处按 ADR-009 放行"推理调用"这一种，禁止任何新的 service→training 依赖。
SERVICE_TRAINING = [
    Allowance(
        rule="service_not_import_training",
        target="packages.service.routers.recommend -> packages.training.inference",
        reason=(
            "调用的是推理入口 generate_recommendations，非训练脚本/训练入口；"
            "README:335 允许 service 调用算法。"
        ),
        basis="ADR-009（docs/decisions.md）；M3 代旭待补专门 ADR 或数据入口层后收紧",
    ),
]

# ---------------------------------------------------------------------------
# 约束 2：生产代码禁止 sys.path / os.chdir
# ---------------------------------------------------------------------------
# 越界位置 conftest.py 与 smoke_test.py 均在 backend/tests/（**测试代码**），
# 不在本约束扫描范围 backend/packages/（生产代码）内，故生产代码当前 0 处越界，
# 此项放行清单为空 —— 测试一旦在 packages/ 下发现 sys.path/os.chdir 即失败。
# 清单点名的 conftest sys.path 属测试引导结构无关机制（见 acceptance/conftest.py），
# 由 P0-1/P0-2 的测试侧边界负责，不作为生产代码架构违规。
PROD_PATH_HACKS: list[Allowance] = []

# ---------------------------------------------------------------------------
# 约束 3：数据目录推算不散落（集中到统一 data 入口）
# ---------------------------------------------------------------------------
# 现状：三个 service router 各算一次 parents[3]/data，training 算 parents[2]。
# 新清单 5.2 指出缺一个 data/index 入口层（归 M2/M3）。单次提交内 M5 不重构
# 他人代码，故登记这 4 处为基线；新增第 5 处即失败。
DATA_DIR_RESOLUTION = [
    Allowance(
        rule="data_dir_not_scattered",
        target="packages/service/routers/health.py:DATA_DIR=parents[3]",
        reason="service router 自算数据目录，存量实现",
        basis="新清单 6.3 M5 P1 / 5.2；M3 待收敛 data 入口层",
    ),
    Allowance(
        rule="data_dir_not_scattered",
        target="packages/service/routers/occupations.py:DATA_DIR=parents[3]",
        reason="service router 自算数据目录，存量实现",
        basis="新清单 6.3 M5 P1 / 5.2；M3 待收敛 data 入口层",
    ),
    Allowance(
        rule="data_dir_not_scattered",
        target="packages/service/routers/recommend.py:DATA_DIR=parents[3]",
        reason="service router 自算数据目录，存量实现",
        basis="新清单 6.3 M5 P1 / 5.2；M3 待收敛 data 入口层",
    ),
    Allowance(
        rule="data_dir_not_scattered",
        target="packages/training/matcher.py:DATA_DIR=parents[2]",
        reason="training 自算数据目录，存量实现",
        basis="新清单 6.3 M5 P1 / 5.2；M2 待收敛 data 入口层",
    ),
]

ALL_ALLOWANCES = SERVICE_TRAINING + PROD_PATH_HACKS + DATA_DIR_RESOLUTION


def allowances_for(rule: str) -> list[Allowance]:
    return [a for a in ALL_ALLOWANCES if a.rule == rule]
