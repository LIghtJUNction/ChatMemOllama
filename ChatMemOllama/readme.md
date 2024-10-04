
# ChatMemOllama 使用说明

## 简介
ChatMemOllama 是一个基于 FastAPI 和 WeChat 的聊天机器人应用，结合了 Ollama 本地 AI 模型和记忆管理功能。该应用能够处理微信消息，进行加密解密，并通过 Ollama 模型生成智能回复。

## 功能
1. **微信消息处理**：接收和处理微信消息，包括文本消息的解析和回复。
2. **消息加密解密**：使用 WeChatCrypto 进行消息的加密和解密，确保通信安全。
3. **记忆管理**：通过 mem0 模块管理用户的聊天记忆，支持记忆的添加和检索。
4. **AI 回复生成**：使用 Ollama 模型生成智能回复，支持异步处理。

## 配置
在 `config` 字典中配置了以下内容：
- **vector_store**：向量存储配置，使用 Qdrant 作为存储提供者。
- **llm**：大语言模型配置，使用 Ollama 模型。
- **embedder**：嵌入模型配置，使用 Ollama 提供的嵌入模型。

## 主要类和函数
### `admin` 类
负责管理微信消息的加密解密、记忆管理和 AI 回复生成。
- **`__init__`**：初始化函数，设置微信参数和 Ollama 客户端。
- **`get_msg_info`**：获取并验证微信请求参数。
- **`decode`**：解密微信消息。
- **`encode`**：加密回复消息。
- **`get`**：处理 GET 请求，返回微信服务器验证字符串。
- **`post`**：处理 POST 请求，解密消息并生成回复。
- **`Admin_notice`**：发送管理员通知。
- **`chat_whth_ollama`**：与 Ollama 模型进行对话，生成回复。
- **`get_memory`**：获取用户的聊天记忆。

## 使用方法
1. 安装依赖：
    ```bash
    pip install fastapi wechatpy uvicorn
    ```
2. 运行应用：
    ```bash
    uvicorn chatmemollama:app --host 0.0.0.0 --port 8000
    ```

## 常见问题
1. **如何配置微信参数？**
    在 `admin` 类的初始化函数中设置 `WECHAT_TOKEN`、`APPID` 和 `EncodingAESKey`。

2. **如何更改 Ollama 模型？**
    修改 `config` 字典中的 `llm` 和 `embedder` 配置，指定新的模型名称和 URL。

3. **如何调试应用？**
    使用 `logging` 模块记录调试信息，日志级别设置为 `DEBUG`。

4. **如何处理异步请求？**
    使用 `async` 和 `await` 关键字处理异步请求，确保在调用异步函数时使用 `await`。

## 结论
ChatMemOllama 是一个功能强大的聊天机器人应用，结合了微信消息处理、记忆管理和 AI 回复生成功能。通过合理配置和使用，可以实现智能化的聊天体验。

# 目前的问题 将在下一个版本解决，本版本仅供测试
