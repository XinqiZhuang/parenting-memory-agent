def memory_exists(
    baby,
    new_memory
):

    new_event = new_memory.get(
        "event",
        ""
    )

    for memory in baby.get(
        "memories",
        []
    ):

        if (
            memory.get("event")
            == new_event
        ):

            return True

    return False