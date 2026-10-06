from types import SimpleNamespace

from app.workers import cron_trigger


def _configure_trigger(monkeypatch):
    monkeypatch.setenv("GITFLOW_API_URL", "https://api.example.test/")
    monkeypatch.setenv("GITFLOW_CRON_SECRET", "test-cron-secret")


def test_cron_trigger_posts_over_https_without_logging_secret(monkeypatch, capsys):
    _configure_trigger(monkeypatch)
    captured = {}

    def fake_post(url, headers, timeout):
        captured.update(url=url, headers=headers, timeout=timeout)
        return SimpleNamespace(
            status_code=200,
            json=lambda: {
                "status": "completed",
                "errors": 0,
                "repositories_checked": 3,
                "repositories_changed": 1,
                "commits_discovered": 2,
                "commits_queued": 2,
            },
        )

    monkeypatch.setattr(cron_trigger.httpx, "post", fake_post)

    assert cron_trigger.main() == 0
    assert captured["url"] == "https://api.example.test/admin/polling/run"
    assert captured["headers"]["Authorization"] == "Bearer test-cron-secret"
    assert "test-cron-secret" not in capsys.readouterr().out


def test_cron_trigger_rejects_http_api_url(monkeypatch, capsys):
    monkeypatch.setenv("GITFLOW_API_URL", "http://api.example.test")
    monkeypatch.setenv("GITFLOW_CRON_SECRET", "test-cron-secret")

    assert cron_trigger.main() == 2
    assert "HTTPS" in capsys.readouterr().err


def test_cron_trigger_fails_when_polling_reports_errors(monkeypatch, capsys):
    _configure_trigger(monkeypatch)

    monkeypatch.setattr(
        cron_trigger.httpx,
        "post",
        lambda *args, **kwargs: SimpleNamespace(
            status_code=503,
            json=lambda: {"status": "completed_with_errors", "errors": 1},
        ),
    )

    assert cron_trigger.main() == 1
    assert "HTTP 503" in capsys.readouterr().err
