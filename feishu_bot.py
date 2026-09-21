"""Feishu adapter: authorized single-family use, durable message receipts, no import-time start."""
import json
import os
import time
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


def extract_post(message):
    content = json.loads(message.content)
    post = content if "content" in content else content.get("zh_cn", next(iter(content.values()), {}))
    text, images = [], []
    for row in post.get("content", []):
        for node in row:
            if node.get("tag") == "text":
                text.append(node.get("text", ""))
            elif node.get("tag") == "img" and node.get("image_key"):
                images.append(node["image_key"])
    return "".join(text).strip(), images


def addressed_to_bot(message):
    if getattr(message, "chat_type", "p2p") != "group":
        return True
    expected_id = os.getenv("FEISHU_BOT_OPEN_ID", "")
    expected_name = os.getenv("FEISHU_BOT_NAME", "育儿助手Agent")
    for mention in message.mentions or []:
        identity = getattr(getattr(mention, "id", None), "open_id", "")
        if (expected_id and identity == expected_id) or (not expected_id and getattr(mention, "name", "") == expected_name):
            return True
    return False


def image_window_open(context_id):
    from agent_v2.service import default_repository
    with default_repository().transaction() as data:
        ctx = data["_agent_v2"]["contexts"].get(context_id, {})
        return time.time() < ctx.get("image_window_until", 0)


def open_image_window(context_id):
    from agent_v2.service import default_repository
    with default_repository().transaction() as data:
        ctx = data["_agent_v2"]["contexts"].setdefault(context_id, {})
        ctx["image_window_until"] = time.time() + 180
    return ("接下来3分钟可以接收你发送的照片。\n群聊中推荐在同一条富文本消息里@我并附上图片，"
            "也可以私聊机器人发图。单独的群图片需平台已开放群消息接收权限。\n每张不超过10MB。")


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
        member = get_family_member(actor_id)
        context_id = f"feishu:{chat_id}:{actor_id}"
        actor_name = member.get("display_name") or actor_id
        addressed = addressed_to_bot(message)
        if not addressed and not (message.message_type == "image" and image_window_open(context_id)):
            return
        if message.message_type == "image":
            image_keys = [json.loads(message.content)["image_key"]]
            text = ""
        elif message.message_type == "post":
            text, image_keys = extract_post(message)
        else:
            text, image_keys = extract_user_text(message), []
        if image_keys:
            from family_features.media import stage_photo, handle_photo_text, MAX_PHOTOS
            from family_features.transport import download_photo
            if len(image_keys) > MAX_PHOTOS:
                reply_text(message.message_id, "一次最多8张照片，请减少数量后重新发送。")
                return
            for index, image_key in enumerate(image_keys):
                content = download_photo(api_client, message.message_id, image_key)
                answer = stage_photo(content, context_id, f"{message.message_id}:image:{index}", actor_name)
            # A caption builds a preview; only a later explicit confirmation writes it.
            if text and text != "上传照片" and answer.startswith("已收到"):
                caption_answer = handle_photo_text(text, context_id, f"{message.message_id}:caption", actor_name)
                if caption_answer is not None:
                    answer = caption_answer
        elif text == "上传照片":
            answer = open_image_window(context_id)
        elif text:
            from family_features.media import handle_photo_text
            answer = handle_photo_text(text, context_id, message.message_id, actor_name)
            if answer is None:
                answer = route_request(text, context_id=context_id, request_id=message.message_id, actor_name=actor_name)
        else:
            answer = "支持文字与静态照片。请发送文字、图片，或在网页上传照片。"
        ok = reply_text(message.message_id, str(answer))
        print("飞书请求处理完成。" if ok else "回复发送失败；已提交操作有回执，不会重复执行。")
    except ValueError as exc:
        reply_text(message.message_id, str(exc))
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
