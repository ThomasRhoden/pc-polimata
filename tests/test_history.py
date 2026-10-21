from datetime import datetime, timedelta, timezone

import pytest

from pc_polimata.core.history import HistoryStore, compare, series

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


@pytest.fixture
def store(tmp_path):
    s = HistoryStore(tmp_path / "h.sqlite3")
    yield s
    s.close()


def test_save_and_list(store):
    a = store.save_run("cpu", {"single_core_score": 100, "multi_core_score": 800}, {"cpu": "X"}, created_at=T0)
    store.save_run("disk", {"write_mb_s": 500, "read_mb_s": 900}, created_at=T0)
    b = store.save_run("cpu", {"single_core_score": 110, "multi_core_score": 760}, created_at=T0 + timedelta(1))
    runs = store.list_runs("cpu")
    assert [r.id for r in runs] == [b, a]  # mais recente primeiro
    assert runs[1].hardware == {"cpu": "X"}
    assert len(store.list_runs()) == 3


def test_persists_across_connections(tmp_path):
    path = tmp_path / "h.sqlite3"
    s = HistoryStore(path)
    s.save_run("memory", {"bandwidth_gb_s": 10, "latency_ns": 80})
    s.close()
    assert len(HistoryStore(path).list_runs("memory")) == 1


def test_rejects_unknown_kind(store):
    with pytest.raises(ValueError):
        store.save_run("gpu", {})


def test_compare_respects_direction(store):
    store.save_run("memory", {"bandwidth_gb_s": 10, "latency_ns": 100}, created_at=T0)
    store.save_run("memory", {"bandwidth_gb_s": 12, "latency_ns": 80}, created_at=T0 + timedelta(1))
    new, old = store.list_runs("memory")
    diff = compare(old, new)
    assert diff["bandwidth_gb_s"]["improvement_percent"] == 20.0
    assert diff["latency_ns"]["improvement_percent"] == 20.0  # latência menor = melhor


def test_compare_different_kinds(store):
    store.save_run("cpu", {})
    store.save_run("disk", {})
    a, b = store.list_runs()
    with pytest.raises(ValueError):
        compare(a, b)


def test_series_and_delete(store):
    first = store.save_run("cpu", {"single_core_score": 1}, created_at=T0)
    store.save_run("cpu", {"single_core_score": 2}, created_at=T0 + timedelta(1))
    assert series(store.list_runs("cpu"), "single_core_score") == [1, 2]
    assert store.delete(first) and not store.delete(first)
    assert store.get(first) is None
