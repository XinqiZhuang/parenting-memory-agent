from baby import load_baby

from query.activity import query_activities


baby = load_baby()


print("所有活动：")

print(
    query_activities(baby)
)


print("大运动活动：")

print(
    query_activities(
        baby,
        category="gross_motor"
    )
)


print("精细动作活动：")

print(
    query_activities(
        baby,
        category="fine_motor"
    )
)