# JUST CHAT

> The simplest way to connect ollama and wechat

最简单的方法让ollama托管的ai模型接入微信

### *前提：*

> 电脑打开浏览器，注册登录你的微信公众号
> 填写你的服务器url
> 推荐~~花生壳，每月免费1g流量，对于完全文字聊天足够了()~~
> 然后映射内网 `127.0.0.1:8000`（任意修改端口）
> 选择 `https/http `然后你得到了一个 网址
> 本程序运行 `/wechat` 路径  因此你在公众号管理网页-基本配置-填写url时:

```
https://xxxx.xxx/wechat
```

`否则你url提交不了`

**至少需要三个参数**
`WECHAT_TOKEN` : 这个token是完全自定义的 例如我设置的token是: lightjunction (区分大小写)
`APPID`：微信公众号唯一的身份标识id
`APPSECRET`：需要妥善保存的密钥,在创建时可见，请务必妥善保存
`EncodingAESKey`：（可选）代码里的示例是开启了加密(填写服务器url)，这个是随机生成的，用来加密操作
