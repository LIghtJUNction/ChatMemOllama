from datetime import time
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse
from Config import Config   # 从Config.py导入Config类
from WeChatMessageHandler import WeChatMessageHandler
from AIsystem import AIsystem
import Guide
import atexit
import uvicorn
import socket

class Main():
    def __init__(self, WeChatMessageHandler, AIsystem):
        self.WeChatMessageHandler = WeChatMessageHandler
        self.AIsystem = AIsystem 
        
    async def GET(self,request):  # 相当于收到GET请求执行的主函数
        msg_info = await WeChatMessageHandler.check(request)
        return msg_info["echo_str"]

    async def POST(self,request):  # 相当于收到POST请求执行的主函数
        msg_info = await WeChatMessageHandler.check(request)
        msg_info = await WeChatMessageHandler.decode(msg_info)
        # 这里开始处理消息 用户提问是 msg_info["msg"].content ， 消息类型：msg_info["msg"].type 用户openid：msg_info["msg"].source 
        Q = msg_info["msg"].content
        msg_info["Q"]=Q

        if msg_info["msg"].type == "text":
            # 这里将问题Q传递给管道处理 看下面
            msg_info = await self.pipe(msg_info)
            
        else: # TODO 先把文本消息处理搞好再考虑支持其他类型!
            A = "暂时不支持非文本消息"

        # 加密响应并回答
        result = await WeChatMessageHandler.encode(msg_info)
        return result
    
    async def pipe(self,msg_info):
        # A = Q,msg_info # TODO
        msg_info = await self.AIsystem.chat(msg_info)
        return msg_info

if __name__ == "__main__":
    # 参考格式如下
    # POST /wechat?signature=待定&timestamp=待定&nonce=待定&openid=待定&encrypt_type=aes&msg_signature=待定 HTTP/1.1
    ChatMemOllama = FastAPI()
    Config = Config()
    WeChatMessageHandler = WeChatMessageHandler(Config)
    AIsystem = AIsystem(Config)
    Main = Main(WeChatMessageHandler,AIsystem)

    # 启动
    @ChatMemOllama.get("/wechat")
    async def wechat_get(request: Request):
        result = await Main.GET(request)  # 这是必须的步骤，直接调用异步函数返回的是一个协程对象 必须用await调用 或者 async.run()
        return PlainTextResponse(content=result)

    @ChatMemOllama.post("/wechat")
    async def wechat_post(request: Request):
        result = await Main.POST(request)
        return PlainTextResponse(content=result)
    
    port = 8000
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('0.0.0.0', port)) == 0:
                print(f"端口冲突:{port} -- 自动切换到下一个端口")
                port += 1
                time.sleep(1)
                continue
            break
    print(f"最终端口:{port}")
    uvicorn.run(ChatMemOllama, host="0.0.0.0", port=port)



