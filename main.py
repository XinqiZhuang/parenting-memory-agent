from router import route_request


print("==============================")
print("Baby Memory Agent")
print("==============================")

print("你可以告诉我宝宝发生的事情，")
print("也可以查询或分析宝宝的成长记录。")
print()
print("输入 exit 可以退出程序。")


while True:

    print()

    user_input = input("你：")

    if user_input.lower() == "exit":
        print("Baby Agent:再见")
        break


    result = route_request(user_input)


    print()
    print("Baby Agent:")
    print(result)