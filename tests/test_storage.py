import json
from datetime import date

from habits import core, schedule, storage


def test_roundtrip(tmp_path):
    path = tmp_path / "nested" / "habits.json"
    store = storage.empty_store()
    core.add_habit(store, "x", date(2026, 6, 24))
    core.mark(store, "x", date(2026, 6, 24), note="hi")
    storage.save(path, store)
    assert storage.load(path) == store


def test_missing_file_is_empty(tmp_path):
    store = storage.load(tmp_path / "absent.json")
    assert store == storage.empty_store()


def test_v1_migration(tmp_path):
    """A v1 file (habits with a `log` list) upgrades to v2 on load."""
    path = tmp_path / "habits.json"
    v1 = {
        "version": 1,
        "habits": {
            "read": {
                "name": "read",
                "created": "2026-06-01",
                "log": ["2026-06-01", "2026-06-02"],
            }
        },
    }
    path.write_text(json.dumps(v1), encoding="utf-8")

    store = storage.load(path)
    assert store["version"] == 2
    habit = store["habits"]["read"]
    assert "log" not in habit
    assert habit["entries"] == {"2026-06-01": {}, "2026-06-02": {}}
    assert habit["schedule"] == schedule.daily()
    assert habit["archived"] is False
    assert habit["tags"] == []
    assert store["config"]["color"] == "auto"

    # And the migrated store still computes streaks correctly.
    assert core.longest_streak(habit["entries"], habit["schedule"],
                               date(2026, 6, 2)) == 2


def test_rejects_non_habits_file(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"nope": 1}), encoding="utf-8")
    try:
        storage.load(path)
    except SystemExit as exc:
        assert "not a valid" in str(exc.code)
    else:  # pragma: no cover
        raise AssertionError("expected SystemExit")
