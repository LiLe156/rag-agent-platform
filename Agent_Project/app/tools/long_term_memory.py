#这里是一个专门负责“总结并写入向量库”、“向粮库检索”工具
import os
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document
from app.config import EMBED_MODEL,BASE_DIR

#长期记忆单独存一个路径避免和知识库混淆
MEMORY_INDEX_PATH = "D:/faiss_memory_store"

print("⌛️正在初始化长期记忆库.;..")
embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL)

#=======================修改点：增加异常捕获，防止因文件损坏导致服务器崩溃============================================
try:
    if os.path.exists(MEMORY_INDEX_PATH):
        memory_db = FAISS.load_local(MEMORY_INDEX_PATH,embeddings,allow_dagerous_deserialization=True)
        print("✅️成功加在本地长期记忆向量库")
    else:
        raise FileNotFoundError
except Exception as e:
    #以下是不存在时创建，可以用os.makedirs()去自动创建
    #用一条占位本文初始化
    print(f"⚠️长期记忆库加载失败（可能文件损坏），正在重新初始化...错误:{e}")

    memory_db = FAISS.from_texts(["系统初始化占位"],embeddings)
    memory_db.delete([memory_db.index_to_docstore_id[0]])
    memory_db.save_local(MEMORY_INDEX_PATH)
    print("✅️长期记忆向量库重新构建完成")


def save_memory(user_id:str,memory_text:str):
    """将总结的关键信息存入长期记忆"""
    if not memory_text or len(memory_text) < 5:
        return
    #metadata元数据
    doc = Document(
        page_content=memory_text,
        metadata={"user_id":user_id,"type":"long_term_memory"}
    )
    memory_db.add_documents([doc])
    memory_db.save_local(MEMORY_INDEX_PATH)

def retriever_memory(user_id:str,query:str,top_k:int=2) -> str:
    """根据用户信息，检索用户的长期记忆"""
    #FAISS支持元数据过滤，只搜索当前用户的记忆
    docs = memory_db.similarity_search(
        query,
        k=top_k,
        filter={"user_id": {"$eq": user_id}}
    )
    # 注意这里的 $eq 操作符
    if not docs:
        return ""
    return "\n".join([d.page_content for d in docs])






















































