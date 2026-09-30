import os
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_classic.retrievers import ContextualCompressionRetriever
from langchain_classic.retrievers.document_compressors import CrossEncoderReranker
from langchain_community.cross_encoders import HuggingFaceCrossEncoder
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from ..config import INDEX_PATH,PDF_PATH,EMBED_MODEL,RERANK_MODEL

print("⌛️正在初始化知识库工具...")
embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL)

if os.path.exists(INDEX_PATH) and os.listdir(INDEX_PATH):
    vector_db = FAISS.load_local(
        INDEX_PATH,
        embeddings,
        allow_dangerous_deserialization=True
    )
    print(f"✅️成功加在本地FAISS向量库")
else:
    print("🏷️为找到向量库，正在重新构建...")
    loader = PyPDFLoader(PDF_PATH)
    docs = loader.load()
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=400,
        chunk_overlap=60
    )
    split_docs = splitter.split_documents(docs)
    vector_db = FAISS.from_documents(split_docs,embeddings)
    vector_db.save_local(INDEX_PATH)
    print("✅️向量构建完成")

base_retriever = vector_db.as_retriever(search_kwargs={"k":4})

try:
    cross_encoder = HuggingFaceCrossEncoder(model_name=RERANK_MODEL,model_kwargs={"device":"cpu"})
    compressor = CrossEncoderReranker(model=cross_encoder,top_n=2)
    final_retriever = ContextualCompressionRetriever(
        base_compressor=compressor,
        base_retriever=base_retriever
    )
    print("✅️Reranker重排模型加载成功")
except Exception as e:
    print(f"⚠️Reranker加载失败，降级使用原始检索器:{e}")
    final_retriever = base_retriever

def search_knowledge(query:str) -> str:
    """查询内部知识库文档，获取业务资料；主观推理、闲聊不要调用"""
    try:
        doc_s = final_retriever.invoke(query)
        if not doc_s:
            return "【检索结果】未找到相关资料"
        content = "\n\n".join([d.page_content for d in doc_s])
        pages = ",".join([str(d.metadata.get("page","未知")) for d in docs])
        return f"【检索结果】\n{content}\n页码:{pages}"
    except Exception as e:
        return f"【检验失败】{str(e)}"
































































































