from app.ai.context_builder import _build_operational_notes


def test_operational_notes_flag_runner_offline_with_doing_tasks():
    priorities, risks = _build_operational_notes(
        {"pending": 0, "doing": 2, "review": 0, "done": 3, "failed": 1},
        "offline",
    )

    assert any("fallidas" in item for item in priorities)
    assert any("runner esta offline" in item for item in priorities)
    assert any("Runner offline" in item for item in risks)

