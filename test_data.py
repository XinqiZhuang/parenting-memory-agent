from baby import load_baby
baby = load_baby()

print("宝宝姓名：", baby["profile"]["name"])
print("出生日期：", baby["profile"]["birth_date"])
print("最近一次体重：", baby["growth_records"][-1]["weight_kg"], "kg")