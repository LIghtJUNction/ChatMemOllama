import logging
import os
import json
import portalocker  # 用于文件锁定
from flask import Flask, request, abort
from wechatpy import parse_message, create_reply
from wechatpy.utils import check_signature
from wechatpy.crypto import WeChatCrypto
from wechatpy.exceptions import InvalidSignatureException, InvalidAppIdException
import asyncio
import ollama

# Flask 应用程序
app = Flask(__name__)

# 配置日志记录
logging.basicConfig(level=logging.DEBUG, format='\033[94m%(levelname)s: \033[93m%(message)s\033[91m')
logger = logging.getLogger(__name__)

# 微信公众号配置
WECHAT_TOKEN = 'xxxxx'
APPID = 'xxxx'
APPSECRET = 'xxxx'
EncodingAESKey = 'xxxx'

# 定义最大聊天记录数
MAX_HISTORY_SIZE = 50

# Ollama AI 初始提示
prompt = '我是一个有趣的聊天机器人,[微笑]\n'

# 用户聊天记录的持久化目录
chat_history_dir = './chat_histories'
os.makedirs(chat_history_dir, exist_ok=True)

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
        return echo_str

    elif request.method == 'POST':
        return handle_post_request(request, msg_signature, timestamp, nonce)

def handle_post_request(request, msg_signature, timestamp, nonce):
    crypto = WeChatCrypto(WECHAT_TOKEN, EncodingAESKey, APPID)
    try:
        msg = crypto.decrypt_message(request.data, msg_signature, timestamp, nonce)
    except (InvalidSignatureException, InvalidAppIdException):
        abort(403)
    else:
        msg = parse_message(msg)
        openid = msg.source  # 获取用户的唯一标识符

        if msg.type == "text":
            reply_content = asyncio.run(handle_ollama_reply(openid, msg.content))
            reply = create_reply(reply_content, msg)
        else:
            reply = create_reply("不支持这个文本类型", msg)

        return crypto.encrypt_message(reply.render(), nonce, timestamp)

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

def save_user_history(openid, messages):
    user_file = os.path.join(chat_history_dir, f"{openid}.json")
    
    # 限制聊天记录数量
    if len(messages) > MAX_HISTORY_SIZE:
        messages = messages[-MAX_HISTORY_SIZE:]  # 只保留最新的k条记录
    
    with open(user_file, 'w', encoding='utf-8') as f:
        portalocker.lock(f, portalocker.LOCK_EX)  # 排他锁（写锁）
        json.dump(messages, f, ensure_ascii=False, indent=2)
        portalocker.unlock(f)

async def handle_ollama_reply(openid, user_input):
    logger.debug(f"用户输入: {user_input}")
    messages = load_user_history(openid)

    messages.append({'role': 'user', 'content': user_input})

    client = ollama.AsyncClient()
    message = {'role': 'assistant', 'content': ''}  # 定义 AI 回复的消息
    content_out = ''

    async for response in await client.chat(model='llama3.1', messages=messages, stream=True):
        if response['done']:
            break
        content = response['message']['content']
        content_out += content
        message['content'] += content

    messages.append(message)
    save_user_history(openid, messages)

    return message['content']

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
