import os
import tempfile

import pending
from router import route_request


def test_router_only_cancels_current_context():

    original_file = pending.PENDING_FILE

    try:
        with tempfile.TemporaryDirectory() as temp_dir:

            pending.PENDING_FILE = os.path.join(
                temp_dir,
                "pending_action.json"
            )

            mother_context = (
                "feishu:test_group:mother"
            )

            father_context = (
                "feishu:test_group:father"
            )

            pending.set_pending_action(
                {
                    "type": "UPDATE_DEVELOPMENT",
                    "candidates": [{}],
                    "new_record": {}
                },
                mother_context
            )

            pending.set_pending_action(
                {
                    "type": "UPDATE_DEVELOPMENT",
                    "candidates": [{}],
                    "new_record": {}
                },
                father_context
            )

            result = route_request(
                "取消",
                context_id=mother_context
            )

            assert result == "已经取消这次修改。"

            assert (
                pending.get_pending_action(
                    mother_context
                )
                is None
            )

            assert (
                pending.get_pending_action(
                    father_context
                )
                is not None
            )

    finally:
        pending.PENDING_FILE = original_file