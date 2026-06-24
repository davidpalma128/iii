import json

import pytest

from habits import cli, storage


def run(tmp_path, *argv):
    data_file = tmp_path / "habits.json"
    rc = cli.main(["--file", str(data_file), "--color", "never", *argv])
    return rc, data_file


def read(data_file):
    return json.loads(data_file.read_text())


def out_of(capsys):
    return capsys.readouterr().out


# --- basics -----------------------------------------------------------------


def test_add_and_list(tmp_path, capsys):
    run(tmp_path, "add", "exercise")
    capsys.readouterr()
    run(tmp_path, "list")
    assert "exercise" in out_of(capsys)


def test_add_with_schedule_and_tags(tmp_path):
    _, df = run(tmp_path, "add", "gym", "--every", "mon,wed,fri",
                "--tag", "health", "--desc", "lift")
    habit = read(df)["habits"]["gym"]
    assert habit["schedule"] == {"type": "weekly", "days": [0, 2, 4]}
    assert habit["tags"] == ["health"]
    assert habit["description"] == "lift"


def test_add_bad_schedule_errors(tmp_path):
    with pytest.raises(SystemExit):
        run(tmp_path, "add", "x", "--every", "blursday")


def test_done_and_undo(tmp_path):
    run(tmp_path, "add", "read")
    _, df = run(tmp_path, "done", "read", "--date", "2026-01-01", "--note", "ch.1")
    assert read(df)["habits"]["read"]["entries"]["2026-01-01"] == {"note": "ch.1"}
    _, df = run(tmp_path, "undo", "read", "--date", "2026-01-01")
    assert read(df)["habits"]["read"]["entries"] == {}


def test_done_unknown_errors(tmp_path):
    with pytest.raises(SystemExit):
        run(tmp_path, "done", "ghost")


def test_rename(tmp_path):
    run(tmp_path, "add", "read")
    run(tmp_path, "done", "read", "--date", "2026-01-01")
    _, df = run(tmp_path, "rename", "read", "reading")
    habits = read(df)["habits"]
    assert "reading" in habits and "read" not in habits


def test_remove(tmp_path):
    run(tmp_path, "add", "read")
    _, df = run(tmp_path, "remove", "read")
    assert "read" not in read(df)["habits"]


# --- archive / today / log --------------------------------------------------


def test_archive_hides_from_list(tmp_path, capsys):
    run(tmp_path, "add", "read")
    run(tmp_path, "archive", "read")
    capsys.readouterr()
    run(tmp_path, "list")
    assert "read" not in out_of(capsys)
    run(tmp_path, "list", "--all")
    assert "read" in out_of(capsys)


def test_today_json(tmp_path, capsys):
    run(tmp_path, "add", "read")
    capsys.readouterr()
    cli.main(["--file", str(tmp_path / "habits.json"), "--json", "today"])
    data = json.loads(out_of(capsys))
    assert any(r["name"] == "read" for r in data)


def test_log_lists_checkins(tmp_path, capsys):
    run(tmp_path, "add", "read")
    run(tmp_path, "done", "read", "--date", "2026-01-01", "--note", "start")
    capsys.readouterr()
    run(tmp_path, "log")
    text = out_of(capsys)
    assert "2026-01-01" in text and "start" in text


def test_stats_json(tmp_path, capsys):
    run(tmp_path, "add", "read", "--every", "3/week")
    run(tmp_path, "done", "read", "--date", "2026-01-01")
    capsys.readouterr()
    cli.main(["--file", str(tmp_path / "habits.json"), "--json", "stats", "read"])
    data = json.loads(out_of(capsys))
    assert data["name"] == "read"
    assert data["schedule"] == "3x / week"
    assert "longest_streak" in data


# --- export / import --------------------------------------------------------


def test_export_csv(tmp_path, capsys):
    run(tmp_path, "add", "read")
    run(tmp_path, "done", "read", "--date", "2026-01-01", "--note", "n1")
    capsys.readouterr()
    cli.main(["--file", str(tmp_path / "habits.json"), "export", "--format", "csv"])
    csv_text = out_of(capsys)
    assert "habit,date,note" in csv_text
    assert "read,2026-01-01,n1" in csv_text


def test_export_import_roundtrip(tmp_path, capsys):
    run(tmp_path, "add", "read")
    run(tmp_path, "done", "read", "--date", "2026-01-01")
    capsys.readouterr()
    cli.main(["--file", str(tmp_path / "habits.json"), "export"])
    export_json = out_of(capsys)
    dump = tmp_path / "dump.json"
    dump.write_text(export_json)

    # import into a fresh file
    fresh = tmp_path / "fresh.json"
    cli.main(["--file", str(fresh), "import", str(dump)])
    assert "read" in json.loads(fresh.read_text())["habits"]


def test_path_command(tmp_path, capsys):
    df = tmp_path / "habits.json"
    cli.main(["--file", str(df), "path"])
    assert str(df) in out_of(capsys)


def test_json_disables_color(tmp_path, capsys):
    run(tmp_path, "add", "read")
    capsys.readouterr()
    cli.main(["--file", str(tmp_path / "habits.json"), "--json", "list"])
    assert "\033[" not in out_of(capsys)
