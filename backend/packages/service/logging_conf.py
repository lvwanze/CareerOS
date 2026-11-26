#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @File       : logging_conf.py
# @Path       : backend/packages/service/logging_conf.py
# @Project    : CareerOS
# @Author     : 2428324206代旭
# @Date       : 2026-11-26 09:00:00
# @Version    : v1.0.0
"""启动时初始化日志：一行一条 JSON，带 request_id（清单 M3 P0-1）。

为什么必须自己做这一步：
    全仓 6 处 logging.getLogger(__name__)，但没有任何一处配置 handler。
    没有 handler 时 Python 走 logging.lastResort（WARNING 及以上才输出），
    所以 matcher.py 里那句 logger.info("推荐完成：...") 从来没打出来过——
    答辩现场"看不见运行过程"就是这么来的。

为什么在模块级调用而不是 startup 事件里：
    uvicorn 启动时会用自己的 dictConfig 配置 uvicorn/uvicorn.error/uvicorn.access
    三个 logger。dictConfig 默认 disable_existing_loggers=True，会把在此之前
    创建的业务 logger 全部禁用；写在 @app.on_event("startup") 里又会晚于
    数据加载与模型初始化，早期日志直接丢。模块级调用（uvicorn 导入 app 时执行）
    时序刚好：uvicorn 的配置已完成，业务代码还没开始跑。

为什么只往 root 加 handler、不动 uvicorn 的 logger：
    uvicorn.access 是访问日志，格式由 uvicorn 自己管；我们只接管业务日志。
    这样终端里会是「uvicorn 的启动横幅 + 业务 JSON 行」，两类信息一眼可分。

幂等：--reload 的每个进程都会 import 一次 main，重复 addHandler 会导致一条
日志打印两遍，所以用 handler 上的私有标记判断。
"""
import json
import logging
import sys

from packages.core.request_context import current_request_id


class JsonLineFormatter(logging.Formatter):
    """把 LogRecord 序列化成单行 JSON，供日志解析方按字段取用。"""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            # 本地时间、到秒即可：答辩演示按时间对齐请求足够用
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            # 关键字段：同一个请求的每条日志都带同一个 id，便于 grep
            "request_id": current_request_id(),
            "msg": record.getMessage(),
        }
        if record.exc_info:
            # 异常堆栈放进独立字段，保持"一行一条"不被换行打断
            payload["exc"] = self.formatException(record.exc_info)
        # ensure_ascii=False：业务文案是中文，转义成 \uXXXX 现场没法看
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(level: str = "INFO") -> None:
    """给 root logger 挂一个 JSON 行 handler；重复调用不会重复挂。"""
    root = logging.getLogger()
    root.setLevel(level.upper())

    for handler in root.handlers:
        if getattr(handler, "_careeros_json", False):
            return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonLineFormatter())
    handler._careeros_json = True  # type: ignore[attr-defined]
    root.addHandler(handler)

    logging.getLogger(__name__).info("日志已初始化 level=%s", level.upper())
