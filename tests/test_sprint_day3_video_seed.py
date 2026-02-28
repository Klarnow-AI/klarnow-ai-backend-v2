from types import SimpleNamespace
import uuid

import app.core.gates as gates
import app.modules.creative.services as creative_services
import app.modules.creative.tools as creative_tools
from app.modules.packs.models import Pack
from app.modules.sprint import services as sprint_services


class _FakeQuery:
    def __init__(self, result):
        self._result = result

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self._result


class _FakeDb:
    def __init__(self, pack):
        self._pack = pack
        self.commit_calls = 0

    def query(self, model):
        if model is Pack:
            return _FakeQuery(self._pack)
        raise AssertionError(f"Unexpected model query: {model}")

    def commit(self):
        self.commit_calls += 1

    def refresh(self, obj):
        return None


def _setup_complete_day(monkeypatch, db, sprint, card):
    monkeypatch.setattr(sprint_services, "get_day_card", lambda *_args, **_kwargs: card)
    monkeypatch.setattr(gates, "can_complete_day", lambda *_args, **_kwargs: (True, ""))
    return sprint_services.complete_day(db, sprint, 3)


def test_day3_completion_seeds_four_videos_when_none_exist(monkeypatch):
    pack_id = uuid.uuid4()
    sprint = SimpleNamespace(id=uuid.uuid4(), pack_id=pack_id, current_day=3, status="active", completed_at=None)
    pack = SimpleNamespace(id=pack_id)
    card = SimpleNamespace(completed_at=None)
    db = _FakeDb(pack)
    calls = []

    monkeypatch.setattr(creative_services, "list_assets_for_pack", lambda *_args, **_kwargs: [])

    def _render_video(**kwargs):
        calls.append(kwargs)
        return {"asset_ids": ["a1", "a2", "a3", "a4"], "type": "video", "count": 4}

    monkeypatch.setattr(creative_tools, "render_video", _render_video)

    _setup_complete_day(monkeypatch, db, sprint, card)

    assert sprint.current_day == 4
    assert card.completed_at is not None
    assert len(calls) == 1
    assert calls[0]["count"] == 4
    assert calls[0]["sprint_day"] == 4


def test_day3_completion_skips_seed_when_videos_exist(monkeypatch):
    pack_id = uuid.uuid4()
    sprint = SimpleNamespace(id=uuid.uuid4(), pack_id=pack_id, current_day=3, status="active", completed_at=None)
    pack = SimpleNamespace(id=pack_id)
    card = SimpleNamespace(completed_at=None)
    db = _FakeDb(pack)
    render_called = False

    monkeypatch.setattr(
        creative_services,
        "list_assets_for_pack",
        lambda *_args, **_kwargs: [SimpleNamespace(type="video")],
    )

    def _render_video(**kwargs):
        nonlocal render_called
        render_called = True
        return {"asset_ids": ["a1"], "type": "video", "count": 1}

    monkeypatch.setattr(creative_tools, "render_video", _render_video)

    _setup_complete_day(monkeypatch, db, sprint, card)

    assert sprint.current_day == 4
    assert card.completed_at is not None
    assert render_called is False


def test_day3_completion_ignores_seed_failures(monkeypatch):
    pack_id = uuid.uuid4()
    sprint = SimpleNamespace(id=uuid.uuid4(), pack_id=pack_id, current_day=3, status="active", completed_at=None)
    pack = SimpleNamespace(id=pack_id)
    card = SimpleNamespace(completed_at=None)
    db = _FakeDb(pack)

    monkeypatch.setattr(creative_services, "list_assets_for_pack", lambda *_args, **_kwargs: [])

    def _render_video(**kwargs):
        raise RuntimeError("video renderer failed")

    monkeypatch.setattr(creative_tools, "render_video", _render_video)

    _setup_complete_day(monkeypatch, db, sprint, card)

    assert sprint.current_day == 4
    assert card.completed_at is not None
    assert db.commit_calls >= 1
