import json
import os
from threading import Lock

import lark_oapi as lark
from dotenv import load_dotenv
from lark_oapi.api.im.v1 import (
    P2ImMessageReceiveV1,
    ReplyMessageRequest,
    ReplyMessageRequestBody,
)

from audit import (
    has_audit_event,
    record_audit_event
)
from family_members import get_family_member
from router import route_request


load_dotenv()

APP_ID = os.getenv("FEISHU_APP_ID")
APP_SECRET = os.getenv("FEISHU_APP_SECRET")

processed_message_ids = set()
request_lock = Lock()


def check_environment() -> None:

    if not APP_ID:
        raise RuntimeError(
            "没有读取到 FEISHU_APP_ID，请检查 .env。"
        )

    if not APP_SECRET:
        raise RuntimeError(
            "没有读取到 FEISHU_APP_SECRET，请检查 .env。"
        )


def extract_user_text(message) -> str:

    if message.message_type != "text":
        return ""

    content = json.loads(message.content)
    user_text = content.get("text", "")

    for mention in message.mentions or []:

        if mention.key:
            user_text = user_text.replace(
                mention.key,
                ""
            )

    return user_text.strip()


def format_agent_result(result) -> str:

    if isinstance(result, str):
        return result

    if result is None:
        return "暂时没有生成回答。"

    return json.dumps(
        result,
        ensure_ascii=False,
        indent=2
    )


def reply_text(
    message_id: str,
    text: str
) -> bool:

    content = json.dumps(
        {"text": text},
        ensure_ascii=False
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
            response.msg
        )

        return False

    print("机器人回复成功。")

    return True


def handle_message(
    data: P2ImMessageReceiveV1
) -> None:

    message = data.event.message
    sender = data.event.sender

    message_id = message.message_id
    chat_id = message.chat_id
    actor_id = sender.sender_id.open_id

    member = get_family_member(
        actor_id
    )

    actor_name = member[
        "display_name"
    ]

    actor_role = member[
        "role"
    ]

    if getattr(
        sender,
        "sender_type",
        ""
    ) == "app":
        return

    with request_lock:

        if (
            message_id in processed_message_ids
            or has_audit_event(message_id)
        ):

            print(
                "忽略已经处理过的消息：",
                message_id
            )

            return

        processed_message_ids.add(
            message_id
        )

        user_text = ""

        try:
            user_text = extract_user_text(
                message
            )

            print(
                "\n收到育儿问题：",
                user_text
            )

            print(
                "发送者：",
                actor_name,
                f"({actor_role})"
            )

            if not user_text:

                answer = "暂时只支持文字消息。"

                reply_succeeded = reply_text(
                    message_id,
                    answer
                )

                record_audit_event(
                    message_id=message_id,
                    chat_id=chat_id,
                    actor_id=actor_id,
                    actor_name=actor_name,
                    actor_role=actor_role,
                    request_text=(
                        f"[{message.message_type}]"
                    ),
                    response_text=answer,
                    status=(
                        "UNSUPPORTED"
                        if reply_succeeded
                        else "REPLY_FAILED"
                    )
                )

                return

            audit_started = record_audit_event(
                message_id=message_id,
                chat_id=chat_id,
                actor_id=actor_id,
                actor_name=actor_name,
                actor_role=actor_role,
                request_text=user_text,
                response_text="",
                status="PROCESSING"
            )

            if not audit_started:

                processed_message_ids.discard(
                    message_id
                )

                reply_text(
                    message_id,
                    "安全日志暂时无法写入，"
                    "本次操作没有执行，请稍后重试。"
                )

                return
            
            context_id = (
                f"feishu:{chat_id}:{actor_id}"
            )

            result = route_request(
                user_text,
                context_id=context_id
            )

            answer = format_agent_result(
                result
            )

            reply_succeeded = reply_text(
                message_id,
                answer
            )

            record_audit_event(
                message_id=message_id,
                chat_id=chat_id,
                actor_id=actor_id,
                actor_name=actor_name,
                actor_role=actor_role,
                request_text=user_text,
                response_text=answer,
                status=(
                    "SUCCESS"
                    if reply_succeeded
                    else "REPLY_FAILED"
                )
            )

        except Exception as error:

            processed_message_ids.discard(
                message_id
            )

            print(
                "处理消息失败：",
                repr(error)
            )

            error_answer = (
                "处理消息时出现错误，请稍后重试。"
            )

            reply_text(
                message_id,
                error_answer
            )

            record_audit_event(
                message_id=message_id,
                chat_id=chat_id,
                actor_id=actor_id,
                actor_name=actor_name,
                actor_role=actor_role,
                request_text=user_text,
                response_text=error_answer,
                status="ERROR",
                error_message=repr(error)
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

    print("育儿 Agent 飞书入口正在运行。")
    print("请保持这个终端窗口开启。")

    ws_client = lark.ws.Client(
        APP_ID,
        APP_SECRET,
        event_handler=event_handler,
        log_level=lark.LogLevel.ERROR
    )

    try:
        ws_client.start()

    except KeyboardInterrupt:
        print(
            "\n育儿 Agent 已安全停止。"
        )