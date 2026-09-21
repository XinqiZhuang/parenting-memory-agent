"""Run as a separate persistent process; --once processes only jobs already due."""
import argparse
import logging
from threading import Event

from dotenv import load_dotenv


def main():
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="只检查一次到期任务，可能真实发送")
    args = parser.parse_args()
    from family_features.scheduler import run_due
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    print("定时服务启动。任务默认关闭；请在网页‘每日推送’配置并开启。")
    stop = Event()
    try:
        while True:
            try:
                results = run_due()
                if results:
                    logging.info("本轮结果：%s", results)
            except Exception as exc:
                logging.error("本轮调度失败：%s（未打印私人内容或凭证）", type(exc).__name__)
                if args.once:
                    raise SystemExit(1)
            if args.once:
                break
            stop.wait(20)
    except KeyboardInterrupt:
        print("定时服务已停止。")


if __name__ == "__main__":
    main()
