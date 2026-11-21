"""Presentation of a configured command, without inventing execution evidence."""


def presentation(run: dict | None) -> tuple[str, str]:
    outcome = (run or {}).get("step_outcome")
    if outcome == "success":
        return ("Command submitted to runner",
                "The run step reported success. This is the configured command submitted "
                "to that step; the step exit status alone does not prove the program started.")
    if outcome == "failure":
        return ("Command submitted to runner",
                "The run step reported failure. This is the configured command submitted "
                "to that step; a failed step alone does not prove the program started.")
    if outcome == "skipped":
        return "Planned command", "The run step was skipped. This command was not executed by that step."
    return ("Planned command",
            "Execution of this command is not established by the recorded step outcome. "
            "Its presence in a manifest is not evidence that it ran.")
