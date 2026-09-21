"""Interactive local setup. Never prints stored secrets; does not call any API."""
import getpass
import os
import secrets
import shutil
from datetime import datetime
from pathlib import Path

from dotenv import dotenv_values, set_key


def main():
    root = Path(__file__).resolve().parent
    path = root / ".env"
    values = dotenv_values(path) if path.exists() else {}
    print("家庭功能配置：直接回车保留原配置。凭证只写入本机.env，不发送给任何服务。")
    changes = {}
    for name, label in (("FEISHU_BOT_NAME", "机器人完整显示名称（默认育儿助手Agent）"),
                        ("FEISHU_PUSH_CHAT_ID", "接收每日推送的群chat_id（oc_开头）"),
                        ("VISION_BASE_URL", "图片模型OpenAI兼容接口地址（不是网页聊天地址）"),
                        ("VISION_MODEL", "支持图片输入的模型ID")):
        entered = input(label + "：").strip()
        if entered:
            changes[name] = entered
    if "VISION_BASE_URL" in changes or values.get("VISION_BASE_URL"):
        entered = getpass.getpass("图片模型API Key（输入不可见，回车保留）：").strip()
        if entered:
            changes["VISION_API_KEY"] = entered
    password = getpass.getpass("家庭网页密码（至少16位，回车保留；本地可以暂不设置）：")
    if password:
        if len(password) < 16:
            raise SystemExit("密码不足16位，本次未写入任何配置，请重新运行。")
        if password != getpass.getpass("再次输入网页密码："):
            raise SystemExit("两次密码不一致，本次未写入。")
        changes["WEB_PASSWORD"] = password
    if changes.get("FEISHU_PUSH_CHAT_ID"):
        chats = {v.strip() for v in (values.get("FEISHU_ALLOWED_CHAT_IDS") or "").split(",") if v.strip()}
        chat = changes["FEISHU_PUSH_CHAT_ID"]
        if chat not in chats:
            if input("将该群加入机器人允许访问的群列表？输入yes确认：").strip() != "yes":
                raise SystemExit("未修改配置。请先确定接收群。")
            chats.add(chat)
            changes["FEISHU_ALLOWED_CHAT_IDS"] = ",".join(sorted(chats))
    if not changes:
        print("没有修改配置。")
        return
    if path.exists():
        # The backup contains secrets: keep it in the ignored runtime directory.
        from storage import data_path
        backup = data_path("config-backups", datetime.now().strftime("env-%Y%m%d-%H%M%S-") + secrets.token_hex(3))
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, backup)
        os.chmod(backup, 0o600)
    path.touch(exist_ok=True)
    for name, value in changes.items():
        set_key(str(path), name, value)
    os.chmod(path, 0o600)
    print("配置已保存。请重启飞书、网页和定时服务。推送仍需在网页中勾选开启。")


if __name__ == "__main__":
    main()
