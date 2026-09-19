import json
import os

import lark_oapi as lark
from dotenv import load_dotenv
from lark_oapi.api.im.v1 import (
    P2ImMessageReceiveV1,
    ReplyMessageRequest,
    ReplyMessageRequestBody,
)


load_dotenv()

APP_ID = os.getenv("FEISHU_APP_ID")
APP_SECRET = os.getenv("FEISHU_APP_SECRET")


def check_environment() -> None:

    if not APP_ID:
        raise RuntimeError(
            "没有读取到 FEISHU_APP_ID，请检查 .env。"
        )

    if not APP_SECRET:
        raise RuntimeError(
            "没有读取到 FEISHU_APP_SECRET，请检查 .env。"
        )


def reply_text(
    message_id: str,
    text: str,
) -> None:

    content = json.dumps(
        {"text": text},
        ensure_ascii=False,
    )

    request = (
        ReplyMessageRequest.builder()
        .message_id(message_id)
        .request_body(
            ReplyMessageRequestBody.builder()
            .msg_type("text")
            .content(content)
            .build()
        )
        .build()
    )

    response = api_client.im.v1.message.reply(
        request
    )

    if not response.success():
        print(
            "回复失败：",
            response.code,
            response.msg,
        )
        return

    print("机器人回复成功。")


def handle_message(
    data: P2ImMessageReceiveV1
) -> None:

    message = data.event.message
    sender = data.event.sender

    print("\n收到飞书消息")
    print("chat_id：", message.chat_id)
    print("message_id：", message.message_id)
    print("message_type：", message.message_type)
    print("content：", message.content)
    print("sender_id：", sender.sender_id.open_id)

    if message.message_type != "text":
        reply_text(
            message.message_id,
            "暂时只支持文字消息。",
        )
        return

    reply_text(
        message.message_id,
        "连接测试成功，我已经收到你的消息。",
    )


check_environment()

api_client = (
    lark.Client.builder()
    .app_id(APP_ID)
    .app_secret(APP_SECRET)
    .log_level(lark.LogLevel.ERROR)
    .build()
)

event_handler = (
    lark.EventDispatcherHandler.builder("", "")
    .register_p2_im_message_receive_v1(
        handle_message
    )
    .build()
)


if __name__ == "__main__":

    print("正在连接飞书……")
    print("连接成功后，请不要关闭这个终端。")

    ws_client = lark.ws.Client(
        APP_ID,
        APP_SECRET,
        event_handler=event_handler,
        log_level=lark.LogLevel.ERROR,
    )

    try:
        client.start()

    except KeyboardInterrupt:
        print("\n飞书连接测试已停止。")