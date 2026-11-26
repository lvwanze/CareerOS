# CareerOS 后端单服务镜像（清单 M3 P0-4）
#
# 设计取舍：
#   * 只打一个镜像，不分前后端——最终形态就是"单服务部署"，service 会 import
#     training 的推理入口（见 ADR-009 / ADR-011），拆成两个镜像反而要处理网络调用。
#   * 工作目录固定 /app/backend：生产代码用 Path(__file__).resolve().parents[N]
#     推算数据目录，必须保持 backend/packages/... 这一层结构，否则 /ready 会 503。
#   * 依赖用 requirements.txt 里的范围号；如需完全复现，把注释里的实测版本锁上。

FROM python:3.11-slim

# PYTHONUNBUFFERED：日志立刻刷出，不然 docker logs 要等缓冲，演示时看不到实时行
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app/backend

# 先只拷依赖清单：改业务代码时这一层仍能命中缓存，重建从几分钟降到几秒
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 再拷代码与数据。数据体积小（三表 + 参考表，十几 MB），直接进镜像，
# 避免挂载卷在演示机器上路径不一致。
COPY backend/packages ./packages
COPY backend/data ./data

EXPOSE 8000

# 单 worker：本项目读表与索引都在进程内缓存，多 worker 只会让缓存各存一份
CMD ["uvicorn", "packages.service.main:app", "--host", "0.0.0.0", "--port", "8000"]
