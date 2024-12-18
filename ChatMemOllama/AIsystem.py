import json
import datetime
import asyncio
import ollama
import openai
from Config import Config
import datetime
from tavily import TavilyClient # pip install tavily-python

class AIsystem:
    def __init__(self, Config):
        self.Config = Config
        self.system_prompt = (
            "你的身份：智能助手\n"
            "你的管理员:LIghtJUNction\n"
            "你的能力：在线搜索以及获取当前时间\n"
            "你的说话方式：对话里带有微信表情符号，例如：[骷髅][捂脸][破涕为笑][憨笑][微笑][色][便便][旺柴][得意][发呆][流泪][微笑][害羞][色][闭嘴][睡][大哭][尴尬][调皮][呲牙][呲牙][惊讶][难过][抓狂][囧][吐][偷笑][愉快][白眼][傲慢][困][惊恐][憨笑][悠闲][咒骂][疑问][嘘][晕][衰][敲打][再见][抠鼻][擦汗][鼓掌][坏笑][右哼哼][鄙视][委屈][快哭了][亲亲][可怜][笑脸][嘿哈][无语][奸笑][生病][加油][机智][打脸][社会社会][好的][爱心][嘴唇][心碎][拥抱][强][合十][拳头][勾引][菜刀][凋谢][咖啡][炸弹][蛋糕][便便][月亮][太阳][庆祝][红包][發][福][烟花][爆竹][猪头][转圈][发抖][发抖]\n"
            "你的对话环境：微信公众号"
        )
        
        self.users = []
        # 初始化 AI 工具和客户端
        self.search_client = TavilyClient(api_key=Config.Tavilykey)
        self.model = self.Config.Model
        self.LlmMode = self.Config.LlmMode
        if self.LlmMode == 'local':
            self.ollama_chat = ollama.AsyncClient().chat
        elif self.LlmMode == 'online':
            key = self.Config.get_nested('llm', 'OnlineConfig', 'APIKey')
            base = self.Config.get_nested('llm', 'OnlineConfig', 'BaseUrl')

            OpenAI_client = openai.OpenAI(
                api_key= key,
                base_url= base
            )

            self.OpenAI_chat = OpenAI_client.chat.completions.create
        else:
            self.LlmMode = 'local'
            print("默认为 local")
        self.tools_ollama = [
#     {
#         "type": "function",
#         "function": {
#             "name": "search_online",
#             "description": "在线搜索，请先翻译为英文再搜索,精简回答,尽量不要使用这个函数",
#             "parameters": {
#                 "type": "object",
#                 "properties": {
#                     "query": {"type": "string", "description": "搜索关键词"},
#                 },
#                 "required": ["query"],
#             },
#         },
#     },

    {
        "type": "function",
        "function": {
            "name": "get_courses",
            "description": "根据指定日期返回该日期的课程信息，如果不指定日期，默认为今天",
            "parameters": {
                "type": "object",
                "properties": {
                    "date_str": {
                        "type": "string",
                        "description": "指定的日期，格式为 'YYYY-MM-DD'，默认为当前日期（今天）"
                    }
                },
                "required": [],
            },
        },
    },
]

        self.tools_openai = [
    {
        "name": "search_online",
        "description": "在线搜索任意内容,简要的回答",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词"
                }
            },
            "required": ["query"]
        }
    },

    {
        "name": "get_courses",
        "description": "根据指定日期返回该日期的课程信息，如果不指定日期，默认为今天",
        "parameters": {
            "type": "object",
            "properties": {
                "date_str": {
                    "type": "string",
                    "description": "指定的日期，格式为 'YYYY-MM-DD'，默认为当前日期（今天）"
                }
            },
            "required": []
        }
    }
]

    def init_messages(self,msg_info):
        msg_info["messages"] = []
        self.save_message(msg_info, "system", self.system_prompt)


    def save_message(self, msg_info, role, content, name=None):
        msg_info["messages"] = [] if "messages" not in msg_info else msg_info["messages"]
        msg_info["k"] = 20 if "k" not in msg_info else msg_info["k"]
        message = {"role": role, "content": content}
        if name:
            message["name"] = name
        if len(msg_info["messages"]) >= msg_info["k"]:
            msg_info["messages"].append(message)
            msg_info["messages"].pop(1)  # 删除最早的一般消息
        else:
            msg_info["messages"].append(message)


    async def chat(self,msg_info):
        """
        聊天主函数
        """
        if msg_info["openid"] not in self.users:
            self.users.append(msg_info["openid"])
            self.init_messages(msg_info)
                        

        if self.LlmMode == 'local':
            NEW_msg_info = await self._chat_ollama(msg_info)
        
        elif self.LlmMode == 'online':
            NEW_msg_info = await self._chat_openai(msg_info)


        return NEW_msg_info




    async def _chat_ollama(self,msg_info):
        if "A" not in msg_info:
            msg_info["A"] = ""
        self.save_message(msg_info, "user", f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {datetime.datetime.now().strftime('%A')}] {msg_info["msg"].content}" )
        UseTool = await self._tool_calling_ollama(msg_info)
        if not UseTool:
            NEW_msg_info = msg_info
            return NEW_msg_info
        async for response in await self.ollama_chat(
            model=self.model,
            messages=msg_info["messages"],
            stream=True
        ):
            msg_info["A"] += response["message"]["content"]
            print(response["message"]["content"],end="",flush=True)

        self.save_message(msg_info,"assistant",msg_info["A"]) 
        
        NEW_msg_info = msg_info


        return NEW_msg_info
    
    async def _chat_openai(self,msg_info):
        msg_info["A"] = "" if "A" not in msg_info else msg_info["A"]
        
        self.save_message(msg_info, "user", f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {datetime.datetime.now().strftime('%A')}] {msg_info['msg'].content}")
        UseTool = await self._tool_calling_openai(msg_info)
        if not UseTool:
            NEW_msg_info = msg_info
            return NEW_msg_info
        
        for response in self.OpenAI_chat(
            model=self.model,
            messages=msg_info["messages"],
            stream=True
        ):
            chunk = response.choices[0].delta.content

            if isinstance(chunk, str):
                msg_info["A"] += chunk
                print(chunk,end="",flush=True)
            else:
                print("对话完毕,debug: ")
                print(response)

        self.save_message(msg_info, "assistant", msg_info["A"])
        NEW_msg_info = msg_info
        return NEW_msg_info

    async def _tool_calling_ollama(self,msg_info):
        """
        调用工具函数，返回工具函数的结果。
        """
        response = self.ollama_chat(
            model=self.model,
            messages=msg_info["messages"],
            tools=self.tools_ollama
        )

        response_data = await response  # 注意response是一个协程对象，需要await获取结果
        print("应该调用的工具?完整响应：", response_data)
        tool_calls = response_data['message'].get('tool_calls')
        
        if tool_calls:
            results = await self._execute_tool_calls_ollama(tool_calls)
            formatted_results = await self._format_results(results)
            self.save_message(msg_info, "tool", formatted_results)
            print("工具调用结果：",formatted_results)
            return True
        else:
            msg_info["A"] = response["message"]["content"]
            print("没有调用工具")
            return False


    async def _tool_calling_openai(self, msg_info):
        """
        调用工具函数，返回工具函数的结果。
        """
        try:
            response = self.OpenAI_chat(
                model=self.model,
                messages=msg_info["messages"],
                functions=self.tools_openai,
                function_call="auto"  # 或者 "none" / "指定函数"
            )
        except Exception as e:
            print(f"AI模型调用失败，错误原因: {str(e)}")
            return False

        print("应该调用的工具?完整响应：", response)

        # 提取 function_call 和 tool_calls
        message = response.choices[0].message
        function_call = getattr(message, 'function_call', None)
        tool_calls = getattr(message, 'tool_calls', None)

        if tool_calls:
            # 执行所有工具调用
            results = await self._execute_tool_calls_openai(tool_calls)
            for result in results:
                if result['success']:
                    self.save_message(msg_info, "function", result['result'], name=result['name'])
                else:
                    self.save_message(msg_info, "function", f"错误: {result['error']}", name=result['name'])
            print("工具调用结果：", results)
            return True
        elif function_call:
            # 如果只有 function_call，包装成列表传递
            results = await self._execute_tool_calls_openai([function_call])
            for result in results:
                if result['success']:
                    self.save_message(msg_info, "function", result['result'], name=result['name'])
                else:
                    self.save_message(msg_info, "function", f"错误: {result['error']}", name=result['name'])
            print("工具调用结果：", results)
            return True
        else:
            # 没有工具调用，提取 content
            content = getattr(message, 'content', None)
            if content:
                msg_info["A"] = content
                print("没有调用工具")
            else:
                msg_info["A"] = ""
                print("AI回复内容为空")
            return False

    async def _execute_tool_calls_ollama(self, tool_calls):
        """
        执行工具调用，返回结果
        """
        results = []
        print("工具调用：", tool_calls)
        for tool_call in tool_calls:
            print("执行:", tool_call)
            func_name = "_" + tool_call["function"]['name']
            args = json.loads(tool_call.get('arguments', '{}'))
            function = getattr(self, func_name, None)
            if function:
                try:
                    result = await function(**args)
                    results.append({'success': True, 'result': result})
                except Exception as e:
                    results.append({'success': False, 'error': str(e)})
            else:
                results.append({'success': False, 'error': f"未找到工具：{func_name}"})
        return results
    
    async def _execute_tool_calls_openai(self, tool_calls):
        """
        执行工具调用，返回结果
        """
        results = []
        print("工具调用：", tool_calls)
        for tool_call in tool_calls:
            print("执行:", tool_call)
            func_name = "_" + tool_call.name
            args = json.loads(tool_call.arguments)
            function = getattr(self, func_name, None)
            if function:
                try:
                    result = await function(**args)
                    results.append({'success': True, 'result': result ,"name": func_name})
                except Exception as e:
                    results.append({'success': False, 'error': str(e) ,"name": func_name})
            else:
                results.append({'success': False, 'error': f"未找到工具：{func_name}"})
        return results

    async def _format_results(self, results):
        formatted_results = []
        for result in results:
            if not result['success']:
                formatted_results.append(f"错误: {result['error']}")
            else:
                formatted_results.append(f"结果: {result['result']}")
        return "\n".join(formatted_results)

    # 工具函数示例
    async def _search_online(self, query="最新的新闻"):
        if len(query) < 5:
            query = "latest " + query
        try:
            search_results = self.search_client.search(query, max_results=3)
            return json.dumps(search_results["results"], ensure_ascii=False, indent=4)
        except Exception as e:
            return f"搜索失败，错误原因: {str(e)}"


    async def _get_courses(self, date_str=None):
        if date_str is None:
            date_str = datetime.datetime.now().strftime('%Y-%m-%d')
    
        # 读取课程信息
        with open('./ChatMemOllama/CoursesInfo.json', 'r', encoding='utf-8') as f:
            class_info = json.load(f)
    
        # 计算查询日期是第几周和星期几
        start_date = datetime.datetime.strptime('2024-09-09', '%Y-%m-%d')  # 学期开始日期
        query_date = datetime.datetime.strptime(date_str, '%Y-%m-%d')
        delta_days = (query_date - start_date).days
        week_k = delta_days // 7 + 1
        target_weekday = query_date.weekday()  # 0-6，对应周一到周日
    
        courses = []
        for course in class_info:
            weeks_str = course.get('weeks', '')
            if weeks_str:
                weeks_list = list(map(int, weeks_str.split(',')))
                if week_k in weeks_list:
                    # 获取课程的星期几
                    course_weekday = datetime.datetime.strptime(course['date'], '%Y-%m-%d').weekday()
                    if course_weekday == target_weekday:
                        # 计算课程在查询日期的实际日期
                        course_date = start_date + datetime.timedelta(weeks=(week_k - 1), days=course_weekday)
                        course_info = {
                            "课程名称": course['course_name'],
                            "日期": course_date.strftime('%Y-%m-%d'),
                            "上课时间": f"{course['start_time']} - {course['end_time']}",
                            "上课地点": course['rooms'][0]['address'] if course['rooms'] else "未指定",
                            "任课老师": course['teachers'][0]['name'] if course['teachers'] else "未指定",
                        }
                        courses.append(course_info)
    
        result = {
            "课程": courses,
            "查询日期": date_str,
            "当前时间": datetime.datetime.now().isoformat()
        }
        return json.dumps(result, ensure_ascii=False, indent=4)


# 示例使用

if __name__ == "__main__":
    Config = Config()
    ai_system = AIsystem(Config=Config)
    async def main():
        # 初始化 AIsystem
        class MessageObject:
            def __init__(self, source: str, content: str):
                self.source = source
                self.content = content

        MessageObject = MessageObject("userid","你好,当前时间是? 最近有什么新闻吗?")
        # 模拟 msg_info
        msg_info = {
            "openid": "user_openid_12345",
            "msg": MessageObject,
            # "model": "llama3.1", # 会被Config里面的覆盖掉,请去Config里面修改
            "k": 3,
            "A": "",
            "messages": []
        }

        while True:
            msg_info["msg"].content=input(f"# admin - {datetime.datetime.now()} >>> ")
            msg_info["A"]=""
            msg_info = await ai_system.chat(msg_info)
            print("AI 回复:", msg_info["A"])

    asyncio.run(main())

