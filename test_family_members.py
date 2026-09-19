import json
import os
import tempfile

import family_members


def test_get_family_member():

    original_file = (
        family_members.MEMBERS_FILE
    )

    try:
        with tempfile.TemporaryDirectory() as temp_dir:

            family_members.MEMBERS_FILE = (
                os.path.join(
                    temp_dir,
                    "family_members.json"
                )
            )

            test_data = {
                "members": {
                    "member-mother": {
                        "display_name": "妈妈",
                        "role": "mother"
                    }
                }
            }

            with open(
                family_members.MEMBERS_FILE,
                "w",
                encoding="utf-8"
            ) as file:
                json.dump(
                    test_data,
                    file,
                    ensure_ascii=False
                )

            mother = (
                family_members.get_family_member(
                    "member-mother"
                )
            )

            assert (
                mother["display_name"]
                == "妈妈"
            )

            assert (
                mother["role"]
                == "mother"
            )

            unknown = (
                family_members.get_family_member(
                    "unknown-member"
                )
            )

            assert (
                unknown["display_name"]
                == "未命名成员"
            )

            assert (
                unknown["role"]
                == "unknown"
            )

    finally:
        family_members.MEMBERS_FILE = (
            original_file
        )