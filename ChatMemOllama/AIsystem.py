import json
import datetime
import asyncio
import ollama
import openai
from tavily import TavilyClient

class AIsystem:
    def __init__(self, model, Config):
        self.model = model
        self.config = Config
        self.system_prompt = (
            "你的身份：智能助手\n"
            "你的能力：在线搜索以及获取当前时间\n"
            "你的说话方式：对话里带有微信表情符号，例如：[骷髅][捂脸][破涕为笑][憨笑][微笑][色][便便][旺柴][得意][发呆][流泪][微笑][害羞][色][闭嘴][睡][大哭][尴尬][调皮][呲牙][呲牙][惊讶][难过][抓狂][囧][吐][偷笑][愉快][白眼][傲慢][困][惊恐][憨笑][悠闲][咒骂][疑问][嘘][晕][衰][敲打][再见][抠鼻][擦汗][鼓掌][坏笑][右哼哼][鄙视][委屈][快哭了][亲亲][可怜][笑脸][嘿哈][无语][奸笑][生病][加油][机智][打脸][社会社会][好的][爱心][嘴唇][心碎][拥抱][强][合十][拳头][勾引][菜刀][凋谢][咖啡][炸弹][蛋糕][便便][月亮][太阳][庆祝][红包][發][福][烟花][爆竹][猪头][转圈][发抖][发抖]\n"
            "你的对话环境：微信公众号"
        )
        self.active_chats = {}
        
        # 初始化 AI 工具和客户端
        self.search_client = TavilyClient(api_key=self.config.get("Tavilykey"))
        
        llm_mode = self.config.get("LlmMode", "local").lower()
        if llm_mode == 'local':
            self.AI_client = ollama.AsyncClient()
        elif llm_mode == 'online':
            api_key = self.config.get_nested('llm', 'OnlineConfig', 'APIKey')
            api_base = self.config.get_nested('llm', 'OnlineConfig', 'BaseUrl')
            openai.api_key = api_key
            openai.api_base = api_base
            self.AI_client = openai.ChatCompletion.acreate
        else:
            raise ValueError(f"未知的 LlmMode: {llm_mode}")
        
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "search_online",
                    "description": "在线搜索，请先翻译为英文再搜索",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "搜索关键词"},
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_time",
                    "description": "获取当前时间",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                },
            }
        ]
    
    async def process_message(self, msg_info):
        """
        处理收到的消息，接受 msg_info，返回新的 msg_info
        """
        openid = msg_info["msg"].source
        content = msg_info["msg"].content

        # 初始化用户会话
        if openid not in self.active_chats:
            self.active_chats[openid] = {
                "done": True,
                "messages": []
            }
            # 添加系统提示词
            self.active_chats[openid]["messages"].append({"role": "system", "content": self.system_prompt})

        # 保存用户消息
        self.active_chats[openid]["messages"].append({"role": "user", "content": content})

        # 调用 AI 模型处理消息
        response_content = await self.call_model(openid)

        # 保存 AI 回复
        self.active_chats[openid]["messages"].append({"role": "assistant", "content": response_content})

        # 更新 msg_info，准备返回
        new_msg_info = msg_info.copy()
        new_msg_info["A"] = response_content

        return new_msg_info

    async def call_model(self, openid):
        """
        调用 AI 模型，获取回复
        """
        messages = self.active_chats[openid]["messages"]
        # 调用模型，使用工具
        try:
            response = await self.AI_client(
                model=self.model,
                messages=messages,
                functions=self.tools,  # OpenAI 使用 'functions' 参数
                function_call="auto"  # 或者 "none" / "指定函数"
            )
        except Exception as e:
            return f"AI模型调用失败，错误原因: {str(e)}"
        
        # 处理工具调用
        tool_calls = response['choices'][0]['message'].get('function_call')
        if tool_calls:
            # 执行工具函数
            tool_results = await self._execute_tool_calls([tool_calls])
            # 将工具结果添加到会话中
            self.active_chats[openid]["messages"].append({"role": "function", "content": tool_results})
            # 将工具结果传递给 AI 模型，再次生成最终回复
            messages.append({"role": "function", "content": tool_results})
            try:
                final_response = await self.AI_client(
                    model=self.model,
                    messages=messages,
                    functions=self.tools,
                    function_call="auto"
                )
                final_content = final_response['choices'][0]['message']['content']
                return final_content
            except Exception as e:
                return f"AI模型调用失败，错误原因: {str(e)}"
        else:
            # 直接返回 AI 回复内容
            content = response['choices'][0]['message']['content']
            return content

    async def _execute_tool_calls(self, tool_calls):
        """
        执行工具调用，返回结果
        """
        results = []
        for tool_call in tool_calls:
            func_name = "_" + tool_call['name']
            args = json.loads(tool_call.get('arguments', '{}'))
            function = getattr(self, func_name, None)
            if function:
                result = await function(**args)
                results.append(result)
            else:
                results.append(f"未找到工具：{func_name}")
        return "\n".join(results)

    # 工具函数示例
    async def _search_online(self, query: str) -> str:
        if len(query) < 5:
            query = "latest " + query
        try:
            search_results = self.search_client.search(query, max_results=1)
            return json.dumps(search_results["results"], ensure_ascii=False, indent=4)
        except Exception as e:
            return f"搜索失败，错误原因: {str(e)}"

    async def _get_time(self) -> str:
        result = {"timestamp": datetime.datetime.now().isoformat()}
        return json.dumps(result, ensure_ascii=False, indent=4)

# 示例使用
if __name__ == "__main__":

    # 模拟 Config 类


    # 初始化配置
    config = Config()
    # 初始化 AIsystem
    ai_system = AIsystem(model=config.get('model'), config=config)

    # 模拟 msg_info
    msg_info = {
        "msg": {
            "source": "user_openid",
            "content": "你好,当前时间是? 最近有什么新闻吗?"
        }
    }

    async def test_ai_system():
        msg_info = await ai_system.process_message(msg_info)
        print("AI 回复:", msg_info["A"])

    asyncio.run(test_ai_system())