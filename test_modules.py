from baby import load_baby

from query.growth import query_weight
from query.development import query_development


baby = load_baby()


print("最新体重：")
print(query_weight(baby))


print("爬行记录：")
print(
    query_development(
        baby,
        target="爬行"
    )
)


print("大运动记录：")
print(
    query_development(
        baby,
        category="大运动"
    )
)