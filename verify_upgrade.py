"""Read-only installation check. Does not print keys or send private records."""
import importlib
import json
import os
import sys
from pathlib import Path


def main():
    import asyncio
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())
    print("Python:", sys.version.split()[0])
    problems = []
    for module in ("pydantic", "dotenv", "openai", "pytest", "pypdf", "sklearn", "lark_oapi"):
        try:
            importlib.import_module(module)
            print(module + ": OK")
        except Exception as exc:
            print(module + ": NOT READY (" + type(exc).__name__ + ")")
            problems.append(module)
    try:
        from dotenv import load_dotenv
        load_dotenv(Path(__file__).parent / ".env")
        from baby import DATA_FILE
        path = Path(DATA_FILE)
        if path.exists():
            with path.open(encoding="utf-8-sig") as file:
                data = json.load(file)
            print("宝宝JSON: OK (只读取校验，未修改)")
            activities = data.get("learning_activities", [])
            missing = sum(not r.get("date") for r in activities)
            print(f"学习活动: {len(activities)}条，其中缺日期{missing}条；升级不会自动删除历史记录。")
        else:
            print("宝宝JSON: 尚未创建，首次运行将使用项目示例数据。")
        for key in ("DEEPSEEK_API_KEY", "FEISHU_APP_ID", "FEISHU_APP_SECRET"):
            print(key + (": 已配置" if os.getenv(key) else ": 未配置"))
        from family_members import load_family_members
        allowed = os.getenv("FEISHU_ALLOWED_CHAT_IDS") or os.getenv("FEISHU_ALLOWED_USER_IDS") or load_family_members()
        print("飞书访问范围: " + ("已配置" if allowed else "未配置；需指定群ID或配置家庭成员"))
    except Exception as exc:
        print("数据/环境检查未通过：", type(exc).__name__)
        problems.append("data")
    if problems:
        raise SystemExit(1)
    print("本地结构检查完成。此结果不等于已验证真实API连通性。")


if __name__ == "__main__":
    main()
