from baby import load_baby

from age import calculate_age_months


baby = load_baby()

birth_date = baby["profile"]["birth_date"]

age_months = calculate_age_months(
    birth_date
)

print("出生日期：", birth_date)
print("当前月龄：", age_months)