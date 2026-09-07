



def memory_exists(baby, new_memory):

    for memory in baby["memories"]:
        if memory["event"] == new_memory["event"]:
            return True 
    return False


from baby import load_baby
from memory import memory_exists

baby = load_baby()
new_memory = {
    "event": "第一次坐地铁",
    "description": "今天第一次坐了地铁"
}

result = memory_exists(baby, new_memory)
print("记忆是否存在：", result)

