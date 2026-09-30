
import os
import shutil
#放在main.py最上面
MEMORY_DB = "D:/agent_memory.sqlite"
if os.path.exists(MEMORY_DB):
    os.remove(MEMORY_DB)
    print("已重置会话记忆")
#重置对话记记忆，不删除FAISS，可以在代码里加上上面功能代码块


INDEX_PATH = "D:/faiss_store"

def auto_clean_broken_index(index_path):
    """自动检测并清理残缺的FAISS库，避免启动卡死"""
    if not os.path.exists(index_path):
        return

    #FAISS必须同时包含这俩个核心文件才能正常加载
    required_files = ["index.faiss","index.pkl"]
    missing_files = [f for f in required_files if not os.path.exists(os.path.join(index_path,f))]

    #如果核心文件缺失，说明上次异常退出吧库弄坏了，强制清理...
    if missing_files:
        print(f"检测到残缺向量库(缺少{missing_files},正在自动清理僵尸文件...")
        try:
            shutil.rmtree(index_path)
            print("✅️残缺文件清理完成。")
        except Exception as e:
            print(f"⚠️清理失败，请手动删除{index_path}文件夹。错误:{str(e)}")
    else:
        print("✅️向量库文件完整，无需清理，直接加载。")
#在程序启动最开始，执行一次智能清理
auto_clean_broken_index(INDEX_PATH)


#下面继续写你原本的import代码....
import time
from app.graph_builder import graph
from app.observability import metrics

if __name__ == "__main__":
    print("\n====企业内部知识库Agent启动====")
    user_id = "user001"
    session_id = "session_001"
    config = {"configurable":{"thread_id":session_id}}
#thread线程
    while True:
        user_query = input("\n请输入问题(exit退出):")
        if user_query.strip().lower() == "exit":
            break

        init_state = {
            "user_id":user_id,"session_id":session_id,"user_query":user_query,
            "tool_calls":[],"info":[],"round":0,"answer":"",
            "safety_triggered":False,"safety_reason":"","trace_data":{}
        }

        start = time.time()
        try:
            result = graph.invoke(init_state,config=config)
            print(f"\n🤔最终回答:{result.get('answer','无')}")
        except Exception as e:
            print(f"\n❌️执行异常:{str(e)}")
            import traceback
            traceback.print_exc()
        print(f"闹钟本轮总耗时:{time.time()-start:.2f}秒")

    print(metrics.report())

































































































