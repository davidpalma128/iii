import json

from habits import cli, storage


def run(tmp_path, *argv):
    """Invoke the CLI against an isolated data file in ``tmp_path``."""
    data_file = tmp_path / "habits.json"
    return cli.main(["--file", str(data_file), *argv]), data_file


def read(data_file):
    return json.loads(data_file.read_text())


def test_add_then_list(tmp_path, capsys):
    rc, data_file = run(tmp_path, "add", "exercise")
    assert rc == 0
    assert "exercise" in read(data_file)["habits"]

    cli.main(["--file", str(data_file), "list"])
    out = capsys.readouterr().out
    assert "exercise" in out


def test_done_marks_today(tmp_path):
    run(tmp_path, "add", "read")
    rc, data_file = run(tmp_path, "done", "read")
    assert rc == 0
    log = read(data_file)["habits"]["read"]["log"]
    assert len(log) == 1


def test_done_with_explicit_date(tmp_path):
    run(tmp_path, "add", "read")
    _, data_file = run(tmp_path, "done", "read", "--date", "2026-01-01")
    assert read(data_file)["habits"]["read"]["log"] == ["2026-01-01"]


def test_done_unknown_habit_errors(tmp_path):
    try:
        run(tmp_path, "done", "ghost")
    except SystemExit as exc:
        assert "no such habit" in str(exc.code)
    else:  # pragma: no cover
        raise AssertionError("expected SystemExit")


def test_undo(tmp_path):
    run(tmp_path, "add", "read")
    run(tmp_path, "done", "read", "--date", "2026-01-01")
    _, data_file = run(tmp_path, "undo", "read", "--date", "2026-01-01")
    assert read(data_file)["habits"]["read"]["log"] == []


def test_remove(tmp_path):
    run(tmp_path, "add", "read")
    _, data_file = run(tmp_path, "remove", "read")
    assert "read" not in read(data_file)["habits"]


def test_stats_runs(tmp_path, capsys):
    run(tmp_path, "add", "read")
    run(tmp_path, "done", "read", "--date", "2026-01-01")
    cli.main(["--file", str(tmp_path / "habits.json"), "stats", "read"])
    out = capsys.readouterr().out
    assert "longest streak" in out


def test_invalid_date_errors(tmp_path):
    run(tmp_path, "add", "read")
    try:
        run(tmp_path, "done", "read", "--date", "not-a-date")
    except SystemExit as exc:
        assert "invalid date" in str(exc.code)
    else:  # pragma: no cover
        raise AssertionError("expected SystemExit")


def test_storage_roundtrip(tmp_path):
    path = tmp_path / "nested" / "habits.json"
    store = storage.empty_store()
    store["habits"]["x"] = {"name": "x", "created": "2026-06-24", "log": []}
    storage.save(path, store)
    assert storage.load(path) == store
