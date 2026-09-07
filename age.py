from datetime import date


def calculate_age_months(birth_date):

    birth = date.fromisoformat(birth_date)
    today = date.today()

    months = (
        (today.year - birth.year) * 12
        + today.month
        - birth.month
    )

    if today.day < birth.day:
        months -= 1

    return months