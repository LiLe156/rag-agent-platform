# 企业级私有化 RAG Agent 智能问答平台

基于 LangChain 1.x + LangGraph 构建的私有化 AI 问答系统，支持文档上传、智能检索、多轮对话、流式输出。

## 技术栈
- Python / LangChain 1.x / LangGraph
- FastAPI / SSE（流式输出）
- FAISS / Milvus（向量库）
- Redis（记忆管理）
- SQLite（元数据存储）
- Docker（容器化部署）

## 核心功能
1. **RAG检索优化**：HyDE、Multi-Query、父子切片、BM25+向量混合检索、Reranker重排
2. **Agent工具调度**：基于LangGraph的多工具Agent，支持知识库检索、计算、时间查询
3. **记忆系统**：Redis实现短期对话记忆 + 长期事实记忆
4. **安全防护**：Prompt注入防御、越权拦截、输出脱敏
5. **工程化部署**：FastAPI + SSE流式接口，Docker容器化

## 项目截图

### 1. 后端服务启动与 LangGraph 运行日志
![终端日志](images/screenshot.png(终端日志).jpg)

### 2. 前端问答演示
![前端界面](images/screenshot.png(前端界面).jpg)

### 3. 项目工程化目录结构
![项目架构](images/screenshot.png(项目架构).jpg)

## 快速开始
```bash
docker-compose up

##前端展示
启动FastAPI服务后，直接浏览器打开'test6.html'即可访问问答界面
