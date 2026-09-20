"""Feishu adapter: authorized single-family use, durable message receipts, no import-time start."""
import json
import os
from concurrent.futures import ThreadPoolExecutor
from threading import BoundedSemaphore

from dotenv import load_dotenv

from family_members import get_family_member, load_family_members
from router import route_request

load_dotenv()
api_client = None
_slots = BoundedSemaphore(32)
_executor = None


def allowed(chat_id, actor_id):
    chats = {x.strip() for x in os.getenv("FEISHU_ALLOWED_CHAT_IDS", "").split(",") if x.strip()}
    actors = {x.strip() for x in os.getenv("FEISHU_ALLOWED_USER_IDS", "").split(",") if x.strip()}
    if chats:
        return chat_id in chats and (not actors or actor_id in actors)
    return actor_id in actors or actor_id in load_family_members()


def extract_user_text(message):
    if message.message_type != "text":
        return ""
    data = json.loads(message.content)
    text = data.get("text", "")
    for mention in message.mentions or []:
        if mention.key:
            text = text.replace(mention.key, "")
    return text.strip()


def reply_text(message_id, text):
    from lark_oapi.api.im.v1 import ReplyMessageRequest, ReplyMessageRequestBody
    success = True
    # Keep reply payloads below practical message-size limits.
    for start in range(0, len(text), 2500):
        request = (ReplyMessageRequest.builder().message_id(message_id).request_body(
            ReplyMessageRequestBody.builder().msg_type("text").content(
                json.dumps({"text": text[start:start + 2500]}, ensure_ascii=False)
            ).build()).build())
        response = api_client.im.v1.message.reply(request)
        if not response.success():
            print("回复失败，错误码：", response.code)
            success = False
    return success


def process_message(data):
    message = data.event.message
    sender = data.event.sender
    if getattr(sender, "sender_type", "") == "app":
        return
    identity = getattr(sender, "sender_id", None)
    actor_id = getattr(identity, "open_id", "") or getattr(identity, "user_id", "")
    chat_id = message.chat_id
    if not actor_id:
        reply_text(message.message_id, "无法识别发送者，本次未执行。")
        return
    if not allowed(chat_id, actor_id):
        # IDs are identifiers, not access tokens. Do not print request contents or secrets.
        print(f"未授权会话：chat_id={chat_id} actor_id={actor_id}")
        reply_text(message.message_id, "此会话尚未获授权。请由项目所有者配置允许的群或用户后重试。")
        return
    try:
        text = extract_user_text(message)
        if not text:
            reply_text(message.message_id, "飞书目前支持文字；照片请从网页的“照片回忆”上传。")
            return
        member = get_family_member(actor_id)
        context_id = f"feishu:{chat_id}:{actor_id}"
        answer = route_request(text, context_id=context_id, request_id=message.message_id,
                               actor_name=member.get("display_name") or actor_id)
        ok = reply_text(message.message_id, str(answer))
        print("飞书请求处理完成。" if ok else "回复发送失败；已提交操作有回执，不会重复执行。")
    except Exception as exc:
        print("飞书处理异常：", type(exc).__name__)
        reply_text(message.message_id, "处理暂时失败，请先查询操作日志再重试。")


def handle_message(data):
    if not _slots.acquire(blocking=False):
        print("请求队列已满，请稍后重试。")
        return
    future = _executor.submit(process_message, data)
    future.add_done_callback(lambda _: _slots.release())


def main():
    global api_client, _executor
    # Python 3.14 no longer creates an event loop implicitly for SDK imports.
    import asyncio
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())
    import lark_oapi as lark
    app_id, app_secret = os.getenv("FEISHU_APP_ID"), os.getenv("FEISHU_APP_SECRET")
    if not app_id or not app_secret:
        raise SystemExit("请在.env配置FEISHU_APP_ID和FEISHU_APP_SECRET。")
    api_client = lark.Client.builder().app_id(app_id).app_secret(app_secret).log_level(lark.LogLevel.ERROR).build()
    _executor = ThreadPoolExecutor(max_workers=4)
    event_handler = (lark.EventDispatcherHandler.builder("", "")
                     .register_p2_im_message_receive_v1(handle_message).build())
    client = lark.ws.Client(app_id, app_secret, event_handler=event_handler, log_level=lark.LogLevel.ERROR)
    print("育儿Agent V2启动。新增/修改/删除需先预览，再回复“确认”。")
    print("仅处理已配置家庭成员或FEISHU_ALLOWED_CHAT_IDS指定群的消息。")
    try:
        client.start()
    except KeyboardInterrupt:
        print("\n停止接收新请求，正在等待已接收请求完成……")
    finally:
        _executor.shutdown(wait=True)


if __name__ == "__main__":
    main()
