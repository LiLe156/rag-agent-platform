import requests
import json


def test_stream_api():
    url = "http://127.0.0.1:8001/chat/stream"
    payload = {
        "user_id": "user001",
        "session_id": "session_test_001",
        "query": "Function Call原理是什么？"
    }

    print("🚀 开始请求流式接口...")

    try:
        response = requests.post(url, json=payload, stream=True, timeout=300)
        if response.status_code != 200:
            print(f"❌ 请求失败: {response.status_code}")
            return

        print("✅ 连接成功，开始接收流式数据...\n")

        buffer = ""  # <--- 【核心修复】设置缓冲区，解决 SSE 被截断的问题

        for chunk in response.iter_content(chunk_size=1024, decode_unicode=False):
            if chunk:
                buffer += chunk.decode('utf-8')

                # 按换行符切分，只要保证 buffer 里保留最后一行不完整的
                lines = buffer.split('\n')
                buffer = lines.pop()  # 把最后可能不完整的一行留在 buffer 里，下次再拼

                for line in lines:
                    line = line.strip()
                    if not line.startswith('data: '):
                        continue

                    try:
                        data = json.loads(line[6:])
                        status = data.get("status")
                        if status == "start":
                            print(f"\n⏳ [{status}] {data['msg']}")
                        elif status == "tool":
                            print(f"🔍 [{status}] {data['msg']}")
                        elif status == "node":
                            print(f"⚙️ [{status}] {data['msg']}")
                        elif status == "stream":
                            # 打字机效果
                            print(data['token'], end="", flush=True)
                        elif status == "done":
                            print(f"\n\n✅ [{status}] {data['msg']}")
                        elif status == "error":
                            print(f"\n❌ [{status}] {data['msg']}")
                    except json.JSONDecodeError:
                        # 如果拼起来还是错的，说明是脏数据，忽略
                        pass

    except Exception as e:
        print(f"\n请求异常: {str(e)}")


if __name__ == "__main__":
    test_stream_api()

















# import requests
# import json
#
#
# def test_stream_api():
#     url = "http://127.0.0.1:8001/chat/stream"  # 【注意】这里加了正确的斜杠
#     payload = {
#         "user_id": "user001",
#         "session_id": "session_test_001",
#         "query": "Function Call原理是什么？"
#     }
#
#     print("🚀 开始请求流式接口...")
#
#     # 使用 stream=True 开启流式接收模式
#     try:
#         response = requests.post(url, json=payload, stream=True, timeout=300)
#         # 【新增1】检查状态码
#         if response.status_code != 200:
#             print(f"❌ 请求失败，状态码: {response.status_code}")
#             print(f"错误详情: {response.text}")
#             return
#         print("✅ 服务端连接成功，开始接收流式数据...\n")
#
#         for chunk in response.iter_content(chunk_size=1024, decode_unicode=False):
#             if chunk:
#                 decoded = chunk.decode('utf-8')
#
#                 # 按 \n 切分（兼容 \r\n）
#                 for line in decoded.replace('\r', '').split('\n'):
#                     line = line.strip()
#                     if not line.startswith('data: '):
#                         continue
#
#                     try:
#                         # 去掉 "data: " 前缀并解析 JSON
#                         data = json.loads(line[6:])
#                     except json.JSONDecodeError:
#                         continue  # 忽略不完整的 JSON 块
#
#                     status = data.get("status")
#                     if status == "start":
#                         print(f"\n⏳ [{status}] {data['msg']}")
#                     elif status == "tool":
#                         print(f"🔍 [{status}] {data['msg']}")
#                     elif status == "node":
#                         print(f"⚙️ [{status}] {data['msg']}")
#                     elif status == "stream":
#                         # 打字机效果
#                         print(data['token'], end="", flush=True)
#                     elif status == "done":
#                         print(f"\n\n✅ [{status}] {data['msg']}")
#                     elif status == "error":
#                         print(f"\n❌ [{status}] {data['msg']}")
#         # # 【修改】使用 iter_content 按块读取，并加上解码
#         # for chunk in response.iter_content(chunk_size=1024, decode_unicode=False):
#         #     if chunk:
#         #         decoded_line = chunk.decode('utf-8')
#         #         # 按换行符切割，因为一个 chunk 里可能包含多行 SSE 数据
#         #         for line in decoded_line.split('\n'):
#         #             if line.strip().startswith('data: '):
#         #                 try:
#         #                     data = json.loads(line.strip()[6:])  # 去掉 "data: " 前缀
#         #
#         #                     # 根据状态类型，美化打印
#         #                     if data.get("status") == "start":
#         #                         print(f"\n⏳ [{data['status']}] {data['msg']}")
#         #                     elif data.get("status") == "tool":
#         #                         print(f"🔍 [{data['status']}] {data['msg']}")
#         #                     elif data.get("status") == "node":
#         #                         print(f"⚙️ [{data['status']}] {data['msg']}")
#         #                     elif data.get("status") == "stream":
#         #                         # 打字机效果
#         #                         print(data['token'], end="", flush=True)
#         #                     elif data.get("status") == "done":
#         #                         print(f"\n\n✅ [{data['status']}] {data['msg']}")
#         #                     elif data.get("status") == "error":
#         #                         print(f"\n❌ [{data['status']}] {data['msg']}")
#         #                 except json.JSONDecodeError:
#         #                     pass  # 忽略不完整的 JSON 块
#
#         # # 逐行读取服务器推过来的数据
#         # for line in response.iter_lines():
#         #     if line:
#         #         decoded_line = line.decode('utf-8')
#         #         # 过滤掉非 data: 开头的空行
#         #         if decoded_line.startswith('data: '):
#         #             data = json.loads(decoded_line[6:])  # 去掉 "data: " 前缀
#         #
#         #             # 根据状态类型，美化打印
#         #             if data.get("status") == "start":
#         #                 print(f"\n⏳ [{data['status']}] {data['msg']}")
#         #             elif data.get("status") == "tool":
#         #                 print(f"🔍 [{data['status']}] {data['msg']}")
#         #             elif data.get("status") == "node":
#         #                 print(f"⚙️ [{data['status']}] {data['msg']}")
#         #             elif data.get("status") == "stream":
#         #                 # 打字机效果：不换行，直接打印字符
#         #                 print(data['token'], end="", flush=True)
#         #             elif data.get("status") == "done":
#         #                 print(f"\n\n✅ [{data['status']}] {data['msg']}")
#         #             elif data.get("status") == "error":
#         #                 print(f"\n❌ [{data['status']}] {data['msg']}")
#     except Exception as e:
#         print(f"\n请求失败: {str(e)}")
#
#
# if __name__ == "__main__":
#     test_stream_api()