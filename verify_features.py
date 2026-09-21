"""Read-only readiness checks; --live-vision uses a generated test shape, never baby photos."""
import argparse
import os
import tempfile
from pathlib import Path

from dotenv import load_dotenv


def main():
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument("--live-vision", action="store_true", help="付费调用一次图片接口，发送自动生成的彩色圆形测试图")
    args = parser.parse_args()
    from PIL import Image, ImageDraw
    from zoneinfo import ZoneInfo
    ZoneInfo("Asia/Shanghai")
    from family_features.settings import load_settings, allowed_push_chat
    from family_features.tips import builtin_tip
    from family_features.records import browse_records
    from agent_v2.store import read_json
    from storage import data_path
    from datetime import date
    print("图片处理、时区：OK")
    data = read_json(data_path("baby.json")) if data_path("baby.json").exists() else {}
    rows = browse_records(data)
    print(f"档案只读校验：{len(rows)}条有效记录；{sum(not r['date'] for r in rows)}条缺有效日期")
    settings = load_settings()
    print("推送接收群：", "已配置且在允许列表" if allowed_push_chat(settings.chat_id) else "未配置/不在允许列表")
    print("日报：", "开启" if settings.summary_enabled else "关闭", "早教：", "开启" if settings.tip_enabled else "关闭")
    builtin_tip(date.today().isoformat())
    print("备用早教摘录出处校验：OK")
    from rag.knowledge_base import knowledge_inventory
    private_books = [row for row in knowledge_inventory() if row["范围"] == "家庭私有" and row["状态"] == "已收录"]
    print(f"早教私有书籍来源：{len(private_books)}本已收录；优先从新书选择，尚未调用模型筛选")
    for key in ("FEISHU_APP_ID", "FEISHU_APP_SECRET", "VISION_API_KEY", "VISION_BASE_URL", "VISION_MODEL", "WEB_PASSWORD"):
        print(key + "：" + ("已配置" if os.getenv(key) else "未配置"))
    from family_features.media import resolve_photo
    missing = 0
    for row in rows:
        for photo in row["record"].get("photos", []):
            try:
                missing += not resolve_photo(photo).is_file()
            except ValueError:
                missing += 1
    print(f"找不到对应文件/路径不合法的照片：{missing}张")
    if args.live_vision:
        import storage
        from family_features.media import store_image
        from family_features.vision import describe_photos
        import io
        with tempfile.TemporaryDirectory(prefix="vision-probe-") as directory:
            original = storage.DATA_DIR
            storage.DATA_DIR = Path(directory)
            try:
                image = Image.new("RGB", (256, 256), "white")
                ImageDraw.Draw(image).ellipse((50, 50, 200, 200), fill="orange")
                output = io.BytesIO(); image.save(output, "PNG")
                result = describe_photos([store_image(output.getvalue())])
                print("图片接口真实调用成功，结构化结果：", result)
                print("请核对描述是否为白底橙色圆形；本次不评估真实宝宝照片识别准确性。")
            finally:
                storage.DATA_DIR = original
    else:
        print("尚未验证外部API；本次没有发送照片或飞书消息。")


if __name__ == "__main__":
    main()
