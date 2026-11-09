import pytest

from conftest import needs_model
from ncm_sudoku.g0 import IDENTITY_KEYS, environment_record, g0_rule, identity_checks, reproduce

ALL_TRUE = {k: True for k in IDENTITY_KEYS}


def test_identity_keys_non_vacuous():
    # Every check must be able to fail: sham restarts at all levels 1..11 replace the
    # model-free write-back, and the override must also be shown to take effect.
    assert "writeback" not in IDENTITY_KEYS
    assert {f"sham_{lv}" for lv in range(1, 12)} <= set(IDENTITY_KEYS)
    assert "zhat_override_effective" in IDENTITY_KEYS
    assert len(IDENTITY_KEYS) == 17


def test_environment_record_keys():
    rec = environment_record()
    for key in ("python", "torch", "numpy", "platform", "torch_threads", "deterministic", "upstream_commit", "checkpoints"):
        assert key in rec


@pytest.mark.parametrize(
    "pct,identity,passed",
    [
        (86.1, ALL_TRUE, True),
        (84.9, ALL_TRUE, False),
        (87.1, ALL_TRUE, True),
        (86.1, {**ALL_TRUE, "noop": False}, False),
        (86.1, {k: True for k in list(IDENTITY_KEYS)[:-1]}, False),
    ],
)
def test_g0_rule(pct, identity, passed):
    r = g0_rule(pct, identity)
    assert r["passed"] is passed
    assert r["changed_output_count"] == "unavailable"


@needs_model
@pytest.mark.slow
def test_identity_checks_all_true(model, released):
    result = identity_checks(model, released[0][:4])
    assert set(result) == set(IDENTITY_KEYS)
    assert all(result.values()), result


@needs_model
@pytest.mark.slow
def test_reproduce_small(model, released):
    puzzles, sols = released
    r = reproduce(model, puzzles[:4], sols[:4], batch_size=4)
    assert r["n"] == 4 and r["batch_size"] == 4
    assert r["official"]["solved_n"] <= 4
    assert r["own"]["solve"] * 100 == pytest.approx(r["official"]["solved_pct"])
