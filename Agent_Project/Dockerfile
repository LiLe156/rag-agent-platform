# 1. 基础镜像：选一个轻量的 Python 版本
FROM python:3.11-slim

# 2. 设置工作目录
WORKDIR /app

# 3. 先复制依赖文件（利用 Docker 缓存加速构建）
COPY requirements.txt .

# 4. 安装依赖（加上国内清华源，大幅加速）
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 5. 复制项目所有代码到容器里
COPY . .

# 6. 暴露 FastAPI 的端口
EXPOSE 8001


#注入Hugging Face国内镜像源，解决容器内网络连接问题
ENV HF_ENDPOINT=https://hf-mirror.com

# 7. 启动命令（注意：这里用的是 uvicorn 直接启动 api_server）
CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "1", "--loop", "asyncio"]


#  重新启动容器
#docker run -d -p 8001:8001 -v C:/Users/XH/.cache/huggingface:/root/.cache/huggingface -v D:/faiss_store:/app/faiss_store -v D:/faiss_memory_store:/app/faiss_memory_store -v D:/agent_memory.sqlite:/app/agent_memory.sqlite --name agent-service agent-project:v1























































































