from app.cli import main


def test_refresh_and_sources_commands(db, capsys):
    assert main(["refresh-jobs"]) == 0
    out = capsys.readouterr().out
    assert "demo/demo: ok fetched=20" in out
    assert main(["sources"]) == 0
    out = capsys.readouterr().out
    assert "Greenhouse Job Board API: not configured" in out and "Demo provider: enabled" in out
