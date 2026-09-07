
import json

DATA_FILE = "data/baby.json"

def save_baby(baby):
    with open(DATA_FILE,"w",encoding="utf-8") as file:
        json.dump(
            baby,
            file,
            ensure_ascii=False,
            indent=4
        )


def load_baby():
    with open(DATA_FILE,"r", encoding="utf-8") as file:
        baby = json.load(file)
    return baby



