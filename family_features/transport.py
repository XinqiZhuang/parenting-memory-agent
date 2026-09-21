import json
import os

class SendRejected(RuntimeError):
    """Server explicitly returned an error; unlike a timeout, delivery is known to fail."""


def ensure_sdk_loop():
    import asyncio
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())


def make_client():
    ensure_sdk_loop()
    import lark_oapi as lark
    app_id, secret = os.getenv("FEISHU_APP_ID"), os.getenv("FEISHU_APP_SECRET")
    if not app_id or not secret:
        raise ValueError("请配置FEISHU_APP_ID和FEISHU_APP_SECRET。")
    return lark.Client.builder().app_id(app_id).app_secret(secret).timeout(30).log_level(lark.LogLevel.ERROR).build()


def send_text(chat_id, text, token, client=None):
    from family_features.settings import allowed_push_chat
    if not allowed_push_chat(chat_id):
        raise SendRejected("接收群不在允许列表。")
    client = client or make_client()
    ensure_sdk_loop()
    from lark_oapi.api.im.v1 import CreateMessageRequest, CreateMessageRequestBody
    request = CreateMessageRequest.builder().receive_id_type("chat_id").request_body(
        CreateMessageRequestBody.builder().receive_id(chat_id).msg_type("text")
        .content(json.dumps({"text": text}, ensure_ascii=False)).uuid(token).build()).build()
    response = client.im.v1.message.create(request)
    if not response.success():
        raise SendRejected(f"飞书拒绝发送，错误码：{response.code}")
    return getattr(response.data, "message_id", "")


def download_photo(client, message_id, image_key):
    ensure_sdk_loop()
    from lark_oapi.api.im.v1 import GetMessageResourceRequest
    from family_features.media import MAX_BYTES
    request = GetMessageResourceRequest.builder().message_id(message_id).file_key(image_key).type("image").build()
    response = client.im.v1.message_resource.get(request)
    if not response.success() or response.file is None:
        raise ValueError(f"下载照片失败，请核对消息资源权限。错误码：{response.code}")
    content = response.file.read(MAX_BYTES + 1)
    if len(content) > MAX_BYTES:
        raise ValueError("照片超过10MB，请压缩后重新发送。")
    return content
