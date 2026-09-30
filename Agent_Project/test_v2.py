import http.client
import json

conn = http.client.HTTPConnection("127.0.0.1", 8001)
headers = {'Content-type': 'application/json'}
payload = json.dumps({
    "user_id": "user001",
    "session_id": "session_test_001",
    "query": "Function Call原理是什么？"
})

conn.request("POST", "/chat/stream", payload, headers)
response = conn.getresponse()
print(f"状态码: {response.status}")

# 逐块读取数据
while True:
    chunk = response.read(1024) # 每次读 1024 字节
    if not chunk:
        break
    # 强制解码并打印
    print(chunk.decode('utf-8'), end="", flush=True)
conn.close()