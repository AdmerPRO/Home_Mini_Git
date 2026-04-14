import runpy
import sys
import types


def test_main_entrypoint_runs_uvicorn_without_reload(monkeypatch):
    captured = {}

    fake_uvicorn = types.SimpleNamespace()

    def fake_run(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs

    fake_uvicorn.run = fake_run
    monkeypatch.setitem(sys.modules, "uvicorn", fake_uvicorn)

    runpy.run_module("main", run_name="__main__")

    assert captured["args"] == ("main:app",)
    assert captured["kwargs"]["host"] == "127.0.0.1"
    assert captured["kwargs"]["port"] == 8000
    assert captured["kwargs"]["reload"] is False
    assert "reload_excludes" not in captured["kwargs"]
