from datetime import date, timedelta
import re


def parse_event_date(user_input):

    today = date.today()

    # 相对时间
    if "前天" in user_input:
        return (today - timedelta(days=2)).isoformat()

    if "昨天" in user_input:
        return (today - timedelta(days=1)).isoformat()

    if "今天" in user_input:
        return today.isoformat()


    # 完整日期，例如：
    # 2026年8月20日
    match = re.search(
        r"(\d{4})年(\d{1,2})月(\d{1,2})日",
        user_input
    )

    if match:

        year = int(match.group(1))
        month = int(match.group(2))
        day = int(match.group(3))

        return date(
            year,
            month,
            day
        ).isoformat()


    # 月日，例如：
    # 8月20日
    match = re.search(
        r"(\d{1,2})月(\d{1,2})日",
        user_input
    )

    if match:

        month = int(match.group(1))
        day = int(match.group(2))

        return date(
            today.year,
            month,
            day
        ).isoformat()


    return None

def calculate_age_months_at_date(
    birth_date,
    event_date
):

    birth = date.fromisoformat(birth_date)
    event = date.fromisoformat(event_date)

    months = (
        (event.year - birth.year) * 12
        + event.month
        - birth.month
    )

    if event.day < birth.day:
        months -= 1

    return months