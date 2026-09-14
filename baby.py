import json
from pathlib import Path


PROJECT_DIR = Path(__file__).parent

DATA_FILE = (
    PROJECT_DIR
    / "data"
    / "baby.json"
)

EXAMPLE_DATA_FILE = (
    PROJECT_DIR
    / "data"
    / "baby.example.json"
)


def save_baby(baby):

    data_file = Path(DATA_FILE)

    data_file.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with data_file.open(
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            baby,
            file,
            ensure_ascii=False,
            indent=4
        )


def load_baby():

    data_file = Path(DATA_FILE)

    example_data_file = Path(
        EXAMPLE_DATA_FILE
    )


    if not data_file.exists():

        if not example_data_file.exists():

            raise FileNotFoundError(
                "没有找到宝宝数据文件，"
                "也没有找到示例数据文件。"
            )

        with example_data_file.open(
            "r",
            encoding="utf-8"
        ) as file:

            example_baby = json.load(
                file
            )

        save_baby(example_baby)


    with data_file.open(
        "r",
        encoding="utf-8"
    ) as file:

        baby = json.load(file)

    return baby