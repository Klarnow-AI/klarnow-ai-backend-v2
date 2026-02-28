from types import SimpleNamespace

from app.modules.packs.onboarding_jobs import ONBOARDING_JOB_KEY, get_onboarding_job_status


def test_get_onboarding_job_status_defaults_when_missing():
    pack = SimpleNamespace(onboarding_answers=None)
    status = get_onboarding_job_status(pack)
    assert status["status"] == "not_started"
    assert status["attempt"] == 0
    assert status["max_attempts"] >= 1


def test_get_onboarding_job_status_reads_stored_job():
    pack = SimpleNamespace(
        onboarding_answers={
            ONBOARDING_JOB_KEY: {
                "job_id": "job-1",
                "status": "running",
                "attempt": 2,
                "max_attempts": 3,
                "queued_at": "2026-01-01T00:00:00+00:00",
                "started_at": "2026-01-01T00:00:01+00:00",
                "completed_at": None,
                "last_error": None,
            }
        }
    )
    status = get_onboarding_job_status(pack)
    assert status["status"] == "running"
    assert status["job_id"] == "job-1"
    assert status["attempt"] == 2
    assert status["max_attempts"] == 3

