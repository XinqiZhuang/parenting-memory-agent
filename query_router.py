
from query.growth import (
    query_weight,
    query_height,
    query_head_circumference
)

from query.development import (
    query_development
)

from query.activity import query_activities

def query_data(baby, query_type, target="", category="" ):

    if query_type == "QUERY_WEIGHT":

        return query_weight(baby)


    elif query_type == "QUERY_HEIGHT":

        return query_height(baby)


    elif query_type in [
        "QUERY_HEAD",
        "QUERY_HEAD_CIRCUMFERENCE"
    ]:

        return query_head_circumference(baby)


    elif query_type == "QUERY_DEVELOPMENT":

        return query_development(
            baby,
            target,
            category
        )
   
    elif query_type == "QUERY_ACTIVITY":

        return query_activities(
        baby,
        category
        )

    else:

        return "这个查询功能暂时还没有实现"


# baby = load_baby()

# user_input = input("请输入你的问题：")

# result = query_data(baby, user_input)

# print(result)