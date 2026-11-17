# CareerOS 工程开发与协作规范

## 1. 项目工程结构

Python 后端及算法主仓库：

```text
careeros/
├── configs/
│   └── settings.yaml
│
├── data/
│   ├── raw/
│   ├── processed/
│   ├── manifest.json
│   └── FROZEN.json
│
├── docs/
│   ├── problem.md
│   ├── data_contract.md
│   ├── api_spec.md
│   ├── development.md
│   └── decisions.md
│
├── packages/
│   ├── core/
│   │   ├── __init__.py
│   │   └── schemas.py
│   │
│   ├── training/
│   │
│   └── service/
│
├── scripts/
│   ├── build_dataset.py
│   ├── train.py
│   └── check_drift.py
│
├── tests/
│
├── requirements.txt
└── README.md
```

Flutter 客户端使用独立仓库：

```text
careeros_flutter/
├── lib/
│   ├── models/
│   ├── pages/
│   ├── services/
│   ├── widgets/
│   └── main.dart
├── assets/
└── pubspec.yaml
```

## 2. 模块职责边界

### core

负责：

- 公共数据模型。
- Pydantic Schema。
- 数据契约定义。
- 统一字段和枚举。

不负责：

- 算法训练。
- API 业务逻辑。
- 前端页面。

### training

负责：

- 数据特征处理。
- 职业匹配算法。
- 算法评估。
- 模型或算法模块导出。

不负责：

- FastAPI 路由。
- 前端交互。
- 用户业务接口。

### service

负责：

- FastAPI 接口。
- 请求校验。
- 数据读取。
- 算法调用。
- 业务流程组织。
- 统一响应和异常处理。

不负责：

- 算法训练入口。
- 直接修改算法内部实现。
- Flutter 页面逻辑。

### Flutter

负责：

- 用户画像填报。
- 推荐结果展示。
- 技能差距展示。
- 发展路径可视化。
- API 请求与状态处理。

不负责：

- 职业推荐算法。
- 职业技能知识库构建。
- 后端业务数据清洗。

## 3. 模块依赖规则

推荐依赖方向：

core ← training

core ← service

training 通过稳定的算法调用接口向 service 提供推理能力。

service 不得直接依赖 training 中的训练脚本或训练入口。

Flutter 通过 HTTP API 与 service 通信，不直接读取 Python 模块。

## 4. Python 代码规范

- 使用 Python 3.x，具体版本由团队统一确认。
- 变量和函数使用 snake_case。
- 类名使用 PascalCase。
- 公共函数应有清晰的参数和返回值。
- 复杂业务逻辑应添加必要注释。
- 避免在代码中硬编码路径、接口地址和密钥。
- 统一通过配置文件管理可变配置。

## 5. 数据管理规范

- 原始数据放在 data/raw。
- 清洗后数据放在 data/processed。
- 原始数据不直接修改。
- 数据处理脚本需要能够重复运行。
- 记录数据来源、采集时间和处理方式。
- 大型数据文件和模型文件不应未经确认直接提交 Git。
- 敏感数据和密钥不得提交到代码仓库。

## 6. Git 协作规范

建议采用以下分支：

- main：稳定主分支。
- feature/frontend：前端相关工作。
- feature/data：数据相关工作。
- feature/model：算法相关工作。
- feature/backend：后端相关工作。
- feature/test：测试相关工作。

实际分支名称可以根据团队习惯调整。

开发要求：

1. 不直接在 main 上进行日常开发。
2. 每个人优先在负责的分支完成工作。
3. 合并前进行基础运行检查。
4. 修改公共文件前提前沟通。
5. 冲突优先由涉及成员共同解决。
6. 每次提交尽量只包含一类清晰的修改。

## 7. Commit 规范

建议采用：

- feat：新增功能。
- fix：修复问题。
- docs：修改文档。
- refactor：重构代码。
- test：增加或修改测试。
- chore：工程配置或杂项。

示例：

```text
feat: add occupation matching algorithm
fix: correct skill level validation
docs: update data contract
test: add recommendation api tests
```

## 8. 测试要求

核心代码应尽可能提供测试。

第一阶段重点测试：

- 用户画像字段校验。
- 技能等级范围。
- 职业技能数据读取。
- 推荐算法输入输出。
- Top-5 排序结果。
- 技能差距计算。
- API 成功响应。
- API 异常输入。
- 前后端完整业务链路。

## 9. 文档维护

公共数据结构发生变化时，同步更新：

- data_contract.md
- schemas.py
- api_spec.md
- 相关测试代码

技术决策发生变化时，更新 decisions.md。

项目运行方式发生变化时，更新 README.md。

## 10. 开发原则

第一阶段优先保证：

1. 能运行。
2. 能联调。
3. 结果合理。
4. 代码结构清晰。
5. 具备后续扩展空间。

不为了追求复杂架构而增加不必要的开发成本。