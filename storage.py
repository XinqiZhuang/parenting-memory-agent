import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()

DATA_DIR = Path(
    os.getenv(
        "PARENTING_DATA_DIR",
        "data"
    )
)


def data_path(*parts):
    return DATA_DIR.joinpath(*parts)