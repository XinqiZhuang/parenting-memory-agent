def validate_baby(baby):
    if not isinstance(baby, dict):
        return False

    if "profile" not in baby:
        return False

    if "feeding_records" not in baby:
        return False

    if "development_milestones" not in baby:
        return False

    if not isinstance(baby["feeding_records"], list):
        return False

    if not isinstance(baby["development_milestones"], list):
        return False

    return True

from baby import load_baby
baby = load_baby()
result = validate_baby(baby)
print("数据是否有效：", result)