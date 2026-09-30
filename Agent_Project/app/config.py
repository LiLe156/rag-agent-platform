import os
from langchain_openai import ChatOpenAI
#强制使用国内镜像站下载模型
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ["HF_ENDPOINT"]="http://hf-mirror.com"


#路径配置
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX_PATH = "D:/faiss_store"
PDF_PATH = os.path.join(BASE_DIR,"test.pdf")
EMBED_MODEL = "BAAI/bge-small-zh-v1.5"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
RERANK_MODEL = r"D:\models"

#LLM配置
#由于在Docker容器里localhost执行的是容器本身，不是的电脑，所以访问Ollama是不用base_url="http://localhost:11434/v1",而是用base_url="http://host.docker.internal:11434/v1"
llm = ChatOpenAI(
    base_url="http://host.docker.internal:11434/v1",
    api_key="ollama",
    model="qwen2.5",
    temperature=0
)

#安全配置
MAX_ROUND = 5





































