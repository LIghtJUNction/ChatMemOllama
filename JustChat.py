# 参考代码如下
import logging
import os
import json
import portalocker  # 用于文件锁定
from flask import Flask, request, abort
from wechatpy import parse_message, create_reply
from wechatpy.utils import check_signature
from wechatpy.crypto import WeChatCrypto
from wechatpy.exceptions import (InvalidSignatureException, InvalidAppIdException,)
import asyncio
import shutil
import argparse
import ollama
import time


# Flask 应用程序
app = Flask(__name__)

# 配置日志记录
logging.basicConfig(level=logging.DEBUG, format='\033[94m%(levelname)s: \033[93m%(message)s\033[91m')

logger = logging.getLogger(__name__)


# 微信公众号配置
WECHAT_TOKEN = '自定义token'
APPID = '公众号id'
APPSECRET = '唯一的密钥'
EncodingAESKey = '随机生成的加密aeskey'

# Ollama AI 初始提示
prompt = '我是Meta研发的llama3.1，尊敬的Meta开发者你好！\n' # 系统提示词

# 用户聊天记录的持久化目录
chat_history_dir = './chat_histories'
os.makedirs(chat_history_dir, exist_ok=True)

# 微信路由处理
@app.route('/wechat', methods=['GET', 'POST'])
def wechat():
    signature = request.args.get('signature')
    timestamp = request.args.get('timestamp')
    nonce = request.args.get('nonce')
    echo_str = request.args.get("echostr", "")
    msg_signature = request.args.get("msg_signature", "")
    logger.debug(f"Signature: {signature}, Msg_Signature: {msg_signature}, Timestamp: {timestamp}, Nonce: {nonce}")
    logger.debug(f"Body: {request.data}")
    logger.debug(f"token: {WECHAT_TOKEN}")
    # 校验请求是否合法
    try:
        check_signature(WECHAT_TOKEN, signature, timestamp, nonce)
    except InvalidSignatureException:
        logger.warning("收到无效的微信签名请求")
        abort(403)


    if request.method == 'GET':
        # 微信服务器验证
        return echo_str

    elif request.method == 'POST':
        # 处理微信消息
        crypto = WeChatCrypto(WECHAT_TOKEN, EncodingAESKey, APPID)
        try:
            msg = crypto.decrypt_message(request.data, msg_signature, timestamp, nonce)
        except (InvalidSignatureException, InvalidAppIdException):
            abort(403)
        else:
            msg = parse_message(msg)
            openid = msg.source  # 获取用户的唯一标识符

            if msg.type == "text":
                # 调用 Ollama 生成回复，传入用户的聊天历史记录
                reply_content = asyncio.run(handle_ollama_reply(openid, msg.content))
                reply = create_reply(reply_content, msg)
            else:
                reply = create_reply("不支持这个文本类型", msg)

            # print("超时测试")
            # time.sleep(3.9)  结论，加起来不能超过5秒，否者微信会认为任务失败并重发请求
            # 也就是必须修改超时限制
            return crypto.encrypt_message(reply.render(), nonce, timestamp)

# 加载用户的聊天历史记录（使用文件锁）
def load_user_history(openid):
    user_file = os.path.join(chat_history_dir, f"{openid}.json")
    if os.path.exists(user_file):
        with open(user_file, 'r', encoding='utf-8') as f:
            portalocker.lock(f, portalocker.LOCK_SH)  # 共享锁（读锁）
            data = json.load(f)
            portalocker.unlock(f)
            return data
    else:
        return [{'role': 'assistant', 'content': prompt}]

# 保存用户的聊天历史记录（使用文件锁）
def save_user_history(openid, messages):
    user_file = os.path.join(chat_history_dir, f"{openid}.json")
    with open(user_file, 'w', encoding='utf-8') as f:
        portalocker.lock(f, portalocker.LOCK_EX)  # 排他锁（写锁）
        json.dump(messages, f, ensure_ascii=False, indent=2)
        portalocker.unlock(f)

# 处理 Ollama AI 回复的逻辑
async def handle_ollama_reply(openid, user_input):
    # 加载该用户的聊天历史记录
    messages = load_user_history(openid)

    # 将用户输入添加到聊天记录中
    messages.append({'role': 'user', 'content': user_input})

    client = ollama.AsyncClient()
    message = {'role': 'assistant', 'content': ''}  # 定义 AI 回复的消息
    content_out = ''

    async for response in await client.chat(model='llama3.1', messages=messages, stream=True): # 非流式传输
        if response['done']:
            break
        content = response['message']['content']
        content_out += content
        message['content'] += content

    # 将 AI 回复添加到该用户的聊天记录中
    messages.append(message)

    # 保存更新后的聊天记录
    save_user_history(openid, messages)

    # 返回 AI 的完整回复
    return message['content']

# 启动 Flask 应用和 Ollama 聊天功能
if __name__ == '__main__':
    # 启动本地服务器
    app.run(host='0.0.0.0', port=8000)



