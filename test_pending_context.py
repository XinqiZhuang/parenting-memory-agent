import os
import tempfile

import pending


def test_pending_actions_are_isolated():

    original_file = pending.PENDING_FILE

    try:
        with tempfile.TemporaryDirectory() as temp_dir:

            pending.PENDING_FILE = os.path.join(
                temp_dir,
                "pending_action.json"
            )

            mother_context = (
                "feishu:family_group:mother"
            )

            father_context = (
                "feishu:family_group:father"
            )

            pending.set_pending_action(
                {
                    "type": "UPDATE_DEVELOPMENT",
                    "owner": "mother"
                },
                mother_context
            )

            pending.set_pending_action(
                {
                    "type": "UPDATE_DEVELOPMENT",
                    "owner": "father"
                },
                father_context
            )

            mother_action = (
                pending.get_pending_action(
                    mother_context
                )
            )

            father_action = (
                pending.get_pending_action(
                    father_context
                )
            )

            assert (
                mother_action["owner"]
                == "mother"
            )

            assert (
                father_action["owner"]
                == "father"
            )

            pending.clear_pending_action(
                mother_context
            )

            assert (
                pending.get_pending_action(
                    mother_context
                )
                is None
            )

            assert (
                pending.get_pending_action(
                    father_context
                )["owner"]
                == "father"
            )

    finally:
        pending.PENDING_FILE = original_file