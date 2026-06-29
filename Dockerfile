# 数智本体引擎 HTTP 服务镜像。
# 密钥不进镜像 —— LLM 凭据运行时从环境变量注入（OpenAICompatibleClient 先读 env）。
#
# 构建：  docker build -t clife-onto-engine .
# 运行：  docker run -p 8000:8000 \
#            -e DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1 \
#            -e DASHSCOPE_API_KEY=sk-xxx \
#            -e LLM_MODEL=qwen3.5-plus \
#            clife-onto-engine
# 文档：  http://localhost:8000/docs
FROM python:3.12-slim

WORKDIR /app

# 服务依赖；nebula3-python 让镜像可选连真 NebulaGraph 后端（ONTO_BACKEND=nebula）
RUN pip install --no-cache-dir "fastapi>=0.110" "uvicorn>=0.29" "openai>=1.40" "PyYAML>=6" \
    "nebula3-python>=3.8"

# 源码（不 COPY 根目录，避免把 llm.local.json 等带进镜像；另见 .dockerignore）
COPY clife_onto_engine ./clife_onto_engine
COPY plugins ./plugins
COPY scripts ./scripts

ENV LLM_MODEL=qwen3.5-plus \
    PYTHONUNBUFFERED=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=8s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=3).status==200 else 1)"

CMD ["python", "scripts/serve.py", "0.0.0.0", "8000"]
