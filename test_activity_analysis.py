from baby import load_baby

from query.activity import query_activities

from activity_analysis import analyze_activities


baby = load_baby()


activities = query_activities(baby)


print("宝宝活动：")
print(activities)


print("\nAI 活动分析：")

result = analyze_activities(
    baby,
    activities
)

print(result)