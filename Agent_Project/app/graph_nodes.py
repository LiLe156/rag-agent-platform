import time
import json
from .state import AgentState
from .config import llm,MAX_ROUND
from .observability import AgentTracer,metrics,mask_sensitive_data
from .security import check_input_injection,validate_tool_permission
from .tools import TOOL_REGISTRY
import re
#引入长期工具记忆工具
from .tools.long_term_memory import save_memory,retriever_memory



def agent_think_node(state:AgentState):
    tracer = AgentTracer(state['user_id'],state['session_id'])

    #1.输入安全检测
    start = time.time()
    is_injection,reason = check_input_injection(state['user_id'])
    if is_injection:
        metrics.record_injection()
        tracer.add_span("safety_check_input",start,state["user_query"],"拦截注入")
        return {'safety_triggered':True,"safety_reason":"injection","trace_data":tracer.export_log(),"answer":""}
    tracer.add_span("safety_check_input",start,state,state["user_query"],"通过")

    #2.轮次上限（防死循环）
    state_rou = state.get("round",0)
    if state_rou >= MAX_ROUND:
        # return {"answer":"已达到最大检索轮次，基于现有信息回答。","trace_data":tracer.export_log()}
        print("⚠️检测到模型原地打转，强制阻止第三次检索。引导其直接回答...")
        #不要直接返回一句废话，而是返回一个引导提示，让模型基于现有信息回答
        return{
            "answer":f"(系统提示:由于模型反复检索相同内容，已被强制停止。请基于目前已收集到的资料直接回答问题。",
            "trace_data":tracer.export_log()
        }

    #3.重复调用检测
    # if len(state['tool_calls']) >= 2:
    #     if state['tool_calls'][-1] == state['tool_calls'][-2]:
    #         return {"answer":"检测到重复调用，停止检索，整理已有信息作答。","trace_data":tracer.export_log()}
    #将3.重复调用检测改成安全读取写法:
    tool_calls = state.get("tool_calls",[])    #取不到就默认给一个空列表
    if len(tool_calls) >= 2:
        if tool_calls[-1] == tool_calls[-2]:
            return {"answer": "检测到重复调用，停止检索，整理已有信息作答。", "trace_data": tracer.export_log()}

    # #------------------------------提取历史对话（保存最近3轮，防止上下文爆掉）-----------------------------
    # #把历史对话拼接进Prompt，并做好防溢出截断
    # history_text = ""
    # if state.get("messages"):
    #     #只取最后4条消息（大约2轮对话），避免承包qwen2.5上下文
    #     #【核心修复】排除最后一条（也就是当前的提问），只取之前的历史
    #     history_messages = state["messages"][:-1]
    #     recent_messages = history_messages[-4:]
    #     for msg in recent_messages:
    #         role = "用户" if msg.type == "human" else "助手"
    #         history_text += f"{role}:{msg.content}\n"

    #4.构造Prompt让LLM决策
    tools_docs = """
    - search_knowledge:查询内部知识库文档，参数query(检索关键词)
    -calculator:执行数学计算，参数expression(如1+1)
    -get_current_time:获取当前时间，参数formate_type(date/time/datetime)
    """
    history_info = "\n".join(state["info"]) if state["info"] else "(暂无)"
    # # 此处Priompt约束太宽松，需要加强一下！！！！！！！！！！！！！！
    #
    # #在构造Prompt的地方加上
    # #1.安全提取长期记忆列表
    # mem_list = state.get("long_term_memory",[])
    # # long_term_mem = "\n".join(state.get("long_term_memory",[]))
    # long_term_mem = "\n".join(mem_list) if mem_list else ""
    # long_term_context = f"【关于该用户的长期记忆】\n" if long_term_mem else ""

    # ================= 【强制提取事实 + 截取最近3轮历史】 =================
    import re

    # 【核心1】遍历所有历史，提取姓名（防止被最近的对话挤掉）
    user_name = "未提供"
    full_history = state.get("messages", [])
    for msg in full_history:
        if msg.type == "human":
            # 匹配 "我叫X" 或 "我是X"
            match = re.search(r'(?:我叫|我是)([\u4e00-\u9fa5]{2,4})', msg.content)
            if match:
                user_name = match.group(1)  # 动态更新，保证是最新的名字

    # 【核心2】截取最近 3 轮对话（保留上下文连贯性）
    history_text = ""
    if full_history:
        # 排除当前提问
        history_messages = full_history[:-1]
        recent_messages = history_messages[-6:]  # 取最近3轮(用户+AI算2条)
        for msg in recent_messages:
            role = "用户" if msg.type == "human" else "助手"
            history_text += f"{role}: {msg.content}\n"

    # 拼接长期记忆
    mem_list = state.get("long_term_memory", [])
    long_term_mem = "\n".join(mem_list) if mem_list else ""
    long_term_context = f"【关于该用户的长期记忆】\n{long_term_mem}\n" if long_term_mem else ""
    # ==========================================================================

    prompt = f"""你是一个智能助手，请根据用户问题决定下一步行动。

    ==================================================
    【最高优先级事实】（必须严格遵守）：
    用户的姓名是：{user_name}
    如果用户询问姓名，请直接回答“你的名字是{user_name}”。绝对不允许回答“未提供”。
    ==================================================

    【关于该用户的历史记忆】
    {long_term_context}

    【最近的历史对话】（请参考这里理解上下文）
    {history_text}

    【已经收集到的资料】
    {history_info}

    【当前用户问题】
    {state['user_query']}

    【规则】
    1. 如果用户问题涉及【最高优先级事实】或【历史对话】中已经包含的信息（如姓名、喜好、之前的讨论），**绝对不要调用任何工具**，直接输出：{{"action": "answer", "content": "你的回答"}}
    2. 只有涉及【公司内部业务、文档细节】时，才调用 search_knowledge 工具。
    3. 如果已有资料足够回答，直接输出：{{"action": "answer", "content": "你的回答"}}
    4. 如果需要调用工具，输出：{{"action": "tool", "tool_name": "工具名", "tool_args": {{"参数名": "参数值"}}}}
    5. 只输出JSON，不要输出其他文字，不要markdown代码块。
示例：
用户问题：Function Call的原理是什么？
输出：{{"action": "answer", "content": "Function Call是..."}}

"""
    # 【严苛规则，必须遵守】
    # 1. 当【已收集的资料】不为空时，你**必须**输出 action="answer"，直接从资料中提取信息回答，**严禁再次调用工具**！
    # 2. 只有当【已收集的资料】为空，且用户的问题真的需要查询内部文档时，才能输出 action="tool"。
    # 3. 用户问原理、概念等通用知识，直接回答，不要调用工具。
    # 4. 只输出JSON，格式如下：
    # {{"action": "answer", "content": "你的回答"}}
    # 或
    # {{"action": "tool", "tool_name": "工具名", "tool_args": {{"参数名": "参数值"}}}}

    start =time.time()
    try:
        raw_output = llm.invoke(prompt).content.strip()
        #==============================【新增的Token统计代码】==========================================
        input_len = len(prompt)    #粗略估算输入字符串
        output_len = len(raw_output)    #粗略估算输出字符数

        #记录到全局监控中（估算比例：1个中文字符≈1.5个token
        metrics.record_tokens(
            input_tokens=int(input_len*1.5),
            output_tokens=int(output_len*1.5)
        )
        #=====================================================================================

        tracer.add_span('llm_decide',start,prompt[:200],raw_output)
    except Exception as e:
        tracer.add_span('llm_decide',start,prompt[:200],"",error=str(e))
        return {"answer":f"LLM调用失败:str(e)","trace_data":tracer.export_log()}

    #JSON解析容错
    try:
        s_idx = raw_output.find("{")
        e_idx = raw_output.rfind("}") + 1
        if s_idx == -1 or e_idx == 0:
            raise ValueError("未找到JSON")
        parsed = json.loads(raw_output[s_idx:e_idx])
        #parse解析
    except Exception as e:
        return {"answer":f"模型输出格式错误，无法解析:{raw_output[:100]}","trace_data":tracer.export_log()}
    #提取Action不管模型输出啥，先提取出来
    action = parsed.get("action","")
    #【新增容错逻辑1：自动不乱反正】=======================
    #如果模型把action直接写成了工具名（比如"get_current_time")
    if action in TOOL_REGISTRY:
        parsed['tool_name'] = action
        action = "tool"

    #模型直接回答
    # if action == "answer":
    #     return {"answer":parsed.get("content","(模型未提供回答内容)"),
    #             "trace_data":tracer.export_log()
    #             }
    #情况A：模型决定直接回答（此时不生成最终回答，把资料打包交给下游的撰写专家）
    if action == "answer":
        #1.拼装当前收集到的所有资料（历史资料+当前这一轮收集的）
        all_context = "\n\n".join(state.get("info",[]))
        if not all_context:
            all_context = "(本次未检索到相关文档资料)"

        #2.给writer_node留一个空壳回答，触发它接收
        return{
            "research_notes":all_context,
            "answer":"",
            "trace_data":tracer.export_log()
        }

    #模型要调用工具
    if action == "tool":
        tool_name = parsed.get("tool_name","")
        tool_args = parsed.get("tool_args",{})
        #新增容错逻辑判断2：修正参数拼写
        if tool_name == "get_current_time":
            if "formate_type" in tool_args:
                tool_args['format_type'] = tool_args.pop('formate_type')
            if "format" in tool_args:
                tool_args['format_type'] = tool_args.pop('format')



        #【修复：防幻觉拦截】如果模型输出tool_name为"none"或空字符，直接当做最终回答处理
        if tool_name == "none" or not tool_name:
            return {
                "answer":parsed.get("content","(模型认为无需调用工具，但未提供回答内容)"),
                "trace_data":tracer.export_log
            }

        ok,reason = validate_tool_permission(state['user_id'],tool_name)
        if not ok:
            print(f"⚠️安全拦截触发！模型选择的工具:{tool_name},拦截的原因:{reason}")
            return {"safety_triggered":True,"safety_reason":reason,"trace_data":tracer.export_log(),"answer":""}

        if tool_name not in TOOL_REGISTRY:
            return {"answer":f"模型幻觉:工具{tool_name}不存在，已拦截。","trace_data":tracer.export_log()}

        start = time.time()
        try:
            result = TOOL_REGISTRY[tool_name](**tool_args)
            tracer.add_span(f"tool_{tool_name}",start,tool_args,result)
        except Exception as e:
            tracer.add_span(f"tool_{tool_name}",start,tool_args,"",error=str(e))
            return {"answer":f"工具执行异常:{str(e)}","trace_data":tracer.export_log()}

        return {
            "tool_calls":state.get('tool_calls',[]) + [{"tool":tool_name,"args":tool_args}],
            "answer":"",
            "info":state.get("info",[]) + [result],
            "round":state_rou + 1,
            "trace_data":tracer.export_log()
        }

    return {"answer":f"大模型行为异常:{raw_output[:100]}","trace_data":tracer.export_log()}


#=========================【新增节点】撰写专家=========================================
def writer_node(state:AgentState):
# """
# 他是检索专家的下游。
# 检索专家已经把资料收集到了state["research_notes"]里，
# 撰写专家只负责把这些资料流畅的回答。
# """
    user_query = state['user_query']
    #后去检索专家收集回来原始资料
    raw_notes = state.get('research_notes',"")

    #提取长期记忆
    mem_list = state.get('long_term_memory',[])
    long_term_mem = "\n".join(mem_list) if mem_list else ""

    print("✍️【撰写专家】正在根据资料申城最终回答...")

    #构建一个专门的“撰写Prompt”，让模型扮演一个专业的编辑
    writer_prompt = f"""你是一个专业的回答撰写专家。请根据以下资料回答用户问题。

【关于该用户的长期记忆】
{long_term_mem}

【检索专家收集到的资料】
{raw_notes}

用户问题:{user_query}

撰写要求:
1.只使用上面资料中的信息回答，绝对不要编造。
2.如果资料里没有答案，直接说“知识没有找到先关内容”。
3.回答要连贯、自然，像人类专家在说话
"""
    #调用大模型
    resp = llm.invoke(writer_prompt)

    #直接返回最终回答
    return {"answer":resp.content}


#【新增节点1】检索长期记忆
def retriever_memory_node(state:AgentState):
    #检索该用户长期记忆
    user_id = state['user_id']
    query = state["user_query"]

    print(f"🤔【长期记忆】正在检索用户{user_id}的历史记忆...")
    memory_context = retriever_memory(user_id,query)
    if memory_context:
        return {"long_term_memory":[memory_context]}
    else:
        return {"long_tem_memory":[]}

#【新增节点2】保存长期记忆
def save_memory_node(state: AgentState):
    """保存长期记忆：用LLM总结对话中的关键事实，而不是死记姓名"""
    user_id = state['user_id']
    user_query = state['user_query']
    answer = state.get('answer', '')

    # 如果这一轮没有任何回答，说明可能异常退出了，不保存
    if not answer:
        return {}
#====================================替换部分=======================================================================================
#     print("💾 [长期记忆] 正在调用大模型提炼关键事实...")
#
#     # 让本地大模型充当“事实提炼器”，只抽取关键信息
#     extract_prompt = f"""
# 你是一个信息提炼助手。请阅读以下对话，提取出任何关于【用户】的长期有效事实（如姓名、职业、偏好、重要业务信息等）。
# 如果没有值得记忆的长期事实，请直接输出：无。
# 如果有，请用最简洁的一句话总结，不要输出其他废话。
# 注意：像“你好”、“我问了一个问题”这种客套话属于无用信息，不要提取。
#
# 用户：{user_query}
# 助手：{answer}
#
# 请输出总结（例如：用户的姓名是季乐。或者：用户喜欢RAG Agent。）：
# """
#     try:
#         # 调用你本地的 qwen2.5 进行轻量总结
#         extract_result = llm.invoke(extract_prompt).content.strip()
#         print(f"📝 [长期记忆] 提炼出的事实：{extract_result}")
#
#         # 如果模型说没有事实，或者输出了废话，就直接返回不存
#         #【和信修改1】在这里进行严格的“脏数据过滤”
#         clean_result = extract_result.strip()
#         if extract_result and "无" not in extract_result and "没有" not in clean_result and len(extract_result) > 5:
#             print(f"💾【长期记忆】成功提炼并保存事实:{clean_result}")
#             # 存入 FAISS 长期记忆向量库
#             save_memory(user_id, clean_result)
#         else:
#             print("【长期记忆】本轮未提炼成有效事实，跳过保存，不产生额外回答")
#     except Exception as e:
#         print(f"⚠️ [长期记忆] 提炼失败，跳过保存。错误：{e}")
# #核心修改2：必须严格返回空字典
#     #告诉LangGraph：“我只是在后台默默做记录，没有产生新的回答，不要覆盖原来的答案
#     return {}
#========================================以上为被替换部分，下部是目标部分======================================================
    # 针对常见的个人事实做正则提取，速度快且不消耗 CPU
    facts_to_save = []

    # 1. 提取姓名
    name_match = re.search(r'(?:我叫|我是)([\u4e00-\u9fa5]{2,4})', user_query)
    if name_match:
        facts_to_save.append(f"用户的姓名是 {name_match.group(1)}。")

    # 2. 提取喜好/偏好
    like_match = re.search(r'我(?:喜欢|爱好是|偏爱)(.+)', user_query)
    if like_match:
        facts_to_save.append(f"用户喜欢 {like_match.group(1).strip('。！？')}。")

    # 如果有提取到事实，就存入 FAISS；没有就不存，绝不调用大模型！
    if facts_to_save:
        for fact in facts_to_save:
            print(f"💾 [长期记忆] 规则提取事实并保存：{fact}")
            save_memory(user_id, fact)
    else:
        print("🔕 [长期记忆] 本轮未提炼出有效事实，跳过保存。")
        # 严格返回空字典，不覆盖 writer 生成的最终回答
    return {}

def safety_refusal_node(state:AgentState):
    reason = state['safety_reason']
    messages = {
        "injection":"您输入中包含可能干扰心痛正常运行的指令，已拒绝执行。",
        "unauthorized_tool":"抱歉，您当前的角色没有权限执行操作。",
        "high_risk_action":"该操作食欲高危行为，需要人工审批。",
    }
    return {"answer":messages.get(reason,"由于安全策略限制，无法满足您的请求")}

def output_node(state:AgentState):
    final_answer = state.get("answer","任务已完成。")
    safe_answer = mask_sensitive_data(final_answer)
    if state.get("trace_data"):
        metrics.record_trace(state["trace_data"])
        print("\n📊全链路日志(Trace):")
        print(json.dumps(state["trace_data"],ensure_ascii=False,indent=2))
    return {"answer":safe_answer}

#此处新增检查critic检察官函数
def critic_node(state:AgentState):
    """这里是对前面的答案、枷锁内容以及info进行审核的检察官"""
    user_query = state.get('user_query','')
    draft_answer = state.get('answer','')
    retry_count = state.get('critic_retry_count',0)

    #安全兜底：如果没写答案，直接打回
    if not draft_answer or len(draft_answer.strip()) < 3:
        return {"critic_retry_count":retry_count+1}
    print(f"🤔【审核专家】正在审查第{retry_count+1}版回答...")

    #构造审核Prompt
    critic_prompt = f"""你是一个严格的审核专家。请检查下面这份回答是否符合要求:
    
用户问题:{user_query}
草稿回答:{draft_answer}

评判标准:
1.回答是否直接针对了用户的问题?有没有跑题?
2.回答是否完全基于已有资料?有没有明显的胡编乱造(幻觉)?
3.回答的语气是否自然、专业?

请只输出一个判断词:
-如果合格，输出:PASS
-如果不合格，输出:FAIL
"""
    try:
        #让Qwen2.5进行审核
        retrieve_result = llm.invoke(critic_prompt).content.strip().upper()
        #.upper: 字符串方法，把字符串里所有小写英文字母转为大写，大写、数字、符号、中文保持不变。
        print(f"📝【审核专家】审查结果:{retrieve_result}")

        if "PASS" in retrieve_result or "合格" in retrieve_result:
            #审核通过，把刚才的判断清净，让流程正常走先去
            return {"critic_retry_count":0}
        else:
            #审核不通过，增加重试次数，把答案清空，触发Writer重写
            print("⚠️【审核专家】回答未通过审核，打回撰写专家重写！")
            return {"critic_retry_count":retry_count+1,"answer":""}

    except Exception as e:
        print(f"⚠️【审核专家】审核异常，默认放行，错误:{e}")
        return {"critic_retry_count":0}


























































































