import numpy as np
import pytest
import torch

from ncm_sudoku import e5stats
from ncm_sudoku.e5pairs import Pair
from ncm_sudoku.e5pilot import w_auc as pilot_w_auc
from ncm_sudoku.e5test import (
    NonFiniteError,
    bootstrap,
    canonical_key,
    check_finite,
    decide,
    eligibility,
    external_index,
    head_probs,
    internal_collisions,
    pair_scores,
    same_inputs,
    screen_pairs,
)
from ncm_sudoku.generate import random_solution
from ncm_sudoku.labels import candidate_mask
from ncm_sudoku.symmetry import apply_symmetry, random_symmetry


def _pair(index, solution, pair_id=None):
    return Pair(a=solution.copy(), b=solution.copy(), solution=solution, pair_id=pair_id or f"test-{index}",
                seed=10, index=index, attempts=(1, 1))


def test_screen_rejects_external_collisions_steps_and_logs():
    external_solution = random_solution(np.random.default_rng(1))
    s0 = random_solution(np.random.default_rng(2))
    s2 = random_solution(np.random.default_rng(3))
    s3 = random_solution(np.random.default_rng(4))
    solutions = [s0, external_solution, s2, s3]
    index = external_index({"external": [("external-id", external_solution)]})

    def make_pair(i):
        return _pair(i, solutions[i])

    accepted, log = screen_pairs(make_pair, index, n=3)

    assert [p.pair_id for p in accepted] == ["test-0", "test-2", "test-3"]
    assert len(log) == 4
    assert log[1] == {"index": 1, "pair_id": "test-1", "accepted": False,
                       "reason": "external_collision", "colliding_id": "external-id"}
    assert all(row["accepted"] and row["reason"] is None for row in (log[0], log[2], log[3]))


def test_screen_propagates_generation_errors():
    def make_pair(i):
        if i == 1:
            raise RuntimeError("boom")
        return _pair(i, random_solution(np.random.default_rng(i)))

    with pytest.raises(RuntimeError):
        screen_pairs(make_pair, {}, n=3)


def test_internal_collisions_lists_both_ids():
    sol = random_solution(np.random.default_rng(5))
    relabelled = apply_symmetry(sol, random_symmetry(np.random.default_rng(6), kind="digit"))
    other = random_solution(np.random.default_rng(7))
    pairs = [_pair(0, sol, "p0"), _pair(1, relabelled, "p1"), _pair(2, other, "p2")]
    assert canonical_key(sol) == canonical_key(relabelled)
    assert internal_collisions(pairs) == [("p0", "p1")]


def test_eligibility_from_labels():
    sol = random_solution(np.random.default_rng(8))
    a = sol.copy()
    a[:21] = 0  # at least one both-empty cell
    b = a.copy()  # identical clue mask -> identical candidates on every both-empty cell
    mask = np.stack([candidate_mask(a), candidate_mask(b)])
    empty = np.stack([a == 0, b == 0])
    elig_a, elig_b = eligibility(mask, empty, n=1)
    assert elig_a.tolist() == [False]
    assert elig_b.tolist() == [True]


# --- Task 2: within-pair scoring, probe inference, decisions and outcomes ---


def test_check_finite_raises_on_nan_and_inf():
    ok = np.array([1.0, 2.0, 3.0])
    check_finite("ok", ok)  # must not raise
    with pytest.raises(NonFiniteError):
        check_finite("has_nan", np.array([1.0, np.nan]))
    with pytest.raises(NonFiniteError):
        check_finite("has_inf", ok, np.array([np.inf]))


def test_pair_scores_identical_inputs_score_half_even_with_1ulp_prediction_gap():
    n = 1
    pred = np.full((2, 81, 9), np.nan)
    pa = 0.6
    pb = np.nextafter(pa, 1.0)  # 1 ulp above pa: a real prediction gap, not a tie
    pred[0, 0, 0] = pa
    pred[1, 0, 0] = pb
    mask = np.zeros((2, 81, 9), dtype=bool)
    mask[0, 0, 0] = True  # candidate for member a only -> discordant bit
    empty = np.zeros((2, 81), dtype=bool)
    empty[:, 0] = True
    same_input = np.zeros((1, 81), dtype=bool)
    same_input[0, 0] = True

    res = pair_scores(pred, mask, empty, same_input, n)

    assert res["n_disc"] == [1]
    assert res["w"] == [0.5]  # identical-input tie rule overrides the real gap
    assert res["w_pilot_rule"] == [0.0]  # pb > pa, candidate member (a) scores 0 without the override


def test_pair_scores_match_pilot_w_auc_without_identical_inputs():
    rng = np.random.default_rng(0)
    n = 5
    mask = (rng.random((2 * n, 81, 9)) > 0.5).astype(np.float64)
    empty = rng.random((2 * n, 81)) > 0.3
    pred = rng.random((2 * n, 81, 9))
    same_input = np.zeros((n, 81), dtype=bool)

    d = {"n_pairs": n, "mask": mask, "empty": empty, "codes_same_1_6": np.zeros(n, dtype=bool)}
    pilot = pilot_w_auc(pred, d)

    res = pair_scores(pred, mask, empty, same_input, n)

    np.testing.assert_allclose(res["w"], pilot["per_pair"], equal_nan=True)
    np.testing.assert_allclose(res["w_pilot_rule"], pilot["per_pair"], equal_nan=True)


def test_same_inputs_exact_equality_per_cell():
    n = 2
    features = np.zeros((2 * n, 81, 3), dtype=np.float32)
    features[0, 5] = [1.0, 2.0, 3.0]
    features[n + 0, 5] = [1.0, 2.0, 3.0]  # pair 0, cell 5: identical
    features[1, 5] = [1.0, 2.0, 3.0]
    features[n + 1, 5] = [1.0, 2.0, 3.5]  # pair 1, cell 5: differs

    same = same_inputs(features, n)

    assert same[0, 5] == True  # noqa: E712
    assert same[1, 5] == False  # noqa: E712


def test_same_inputs_zero_and_negative_zero_are_not_identical():
    n = 1
    features = np.zeros((2 * n, 81, 1), dtype=np.float32)
    features[0, 0, 0] = 0.0
    features[n + 0, 0, 0] = -0.0
    assert features[0, 0, 0] == features[n + 0, 0, 0]  # equal as floats (IEEE 754)

    same = same_inputs(features, n)

    assert same[0, 0] == False  # noqa: E712 -- but not bit-identical


def _random_head_state_dict(rng: np.random.Generator, in_dim: int) -> dict:
    model = torch.nn.Sequential(torch.nn.Linear(in_dim, 9), torch.nn.Sigmoid())
    with torch.no_grad():
        model[0].weight.copy_(torch.from_numpy(rng.standard_normal((9, in_dim)).astype(np.float32)))
        model[0].bias.copy_(torch.from_numpy(rng.standard_normal(9).astype(np.float32)))
    return {k: v.clone() for k, v in model.state_dict().items()}


def test_head_probs_seed_mean_is_float32_like_pilot():
    rng = np.random.default_rng(1)
    n_puzzles, feat_dim = 6, 4
    in_dim = feat_dim + 81
    state_dicts = [_random_head_state_dict(rng, in_dim) for _ in range(3)]
    features = rng.standard_normal((n_puzzles, 81, feat_dim)).astype(np.float32)
    empty = rng.random((n_puzzles, 81)) > 0.5

    per_seed, pred = head_probs(state_dicts, features, empty, batch=50)

    assert per_seed.shape == (3, int(empty.sum()), 9)
    assert per_seed.dtype == np.float32
    mean = np.mean(per_seed, axis=0)
    assert mean.dtype == np.float32
    expected = np.full((n_puzzles, 81, 9), np.nan, dtype=np.float64)
    expected[empty] = mean
    assert pred.dtype == np.float64
    np.testing.assert_array_equal(pred, expected)  # bit-for-bit, NaN pattern included


def test_head_probs_independent_of_batch_size():
    rng = np.random.default_rng(2)
    n_puzzles, feat_dim = 20, 3
    in_dim = feat_dim + 81
    state_dicts = [_random_head_state_dict(rng, in_dim) for _ in range(3)]
    features = rng.standard_normal((n_puzzles, 81, feat_dim)).astype(np.float32)
    empty = rng.random((n_puzzles, 81)) > 0.5

    per_seed_50, pred_50 = head_probs(state_dicts, features, empty, batch=50)
    per_seed_7, pred_7 = head_probs(state_dicts, features, empty, batch=7)

    # A single-float32-ulp tolerance, not exact equality: PyTorch's CPU vectorized
    # sigmoid kernel splits work by grain size, so the tail/remainder lanes of a
    # chunked call can round 1 ulp differently from an unchunked call over the same
    # rows (confirmed non-associativity of the vectorized kernel, not a bug in the
    # batching here -- the underlying Linear/matmul step is exactly batch invariant).
    np.testing.assert_allclose(per_seed_50, per_seed_7, atol=2e-6, rtol=0)
    np.testing.assert_allclose(pred_50, pred_7, atol=2e-6, rtol=0)


def test_decide_hand_computed_case():
    # Three pairs with n_disc 1, 4 and 9, built through pair_scores: pair 0 and 1
    # score 1.0 on every discordant bit; pair 2 has 6 wins and 3 exact ties (score
    # 0.5), so w = 7.5 / 9. The unweighted (equal-pair-weight) mean of w -- what
    # the protocol uses -- differs from the bit-pooled mean over all 14 bits.
    n = 3
    pred = np.full((2 * n, 81, 9), 0.5)
    mask = np.zeros((2 * n, 81, 9), dtype=bool)
    empty = np.zeros((2 * n, 81), dtype=bool)
    same_input = np.zeros((n, 81), dtype=bool)

    mask[0, 0, 0] = True  # pair 0: 1 discordant bit, candidate wins
    pred[0, 0, 0], pred[n + 0, 0, 0] = 0.9, 0.1
    empty[0, 0] = empty[n + 0, 0] = True

    for c in range(4):  # pair 1: 4 discordant bits, candidate wins every time
        mask[1, c, 0] = True
        pred[1, c, 0], pred[n + 1, c, 0] = 0.9, 0.1
        empty[1, c] = empty[n + 1, c] = True

    for c in range(9):  # pair 2: 9 discordant bits, 6 wins and 3 exact ties
        mask[2, c, 0] = True
        if c < 6:
            pred[2, c, 0], pred[n + 2, c, 0] = 0.9, 0.1
        else:
            pred[2, c, 0], pred[n + 2, c, 0] = 0.5, 0.5
        empty[2, c] = empty[n + 2, c] = True

    scores = pair_scores(pred, mask, empty, same_input, n)
    assert scores["n_disc"] == [1, 4, 9]
    w_p2 = np.array(scores["w"])
    np.testing.assert_allclose(w_p2, [1.0, 1.0, 7.5 / 9])

    n_disc = np.array(scores["n_disc"], dtype=np.float64)
    unweighted_mean = float(np.mean(w_p2))  # equal pair weight
    bit_pooled_mean = float((w_p2 * n_disc).sum() / n_disc.sum())
    assert unweighted_mean != pytest.approx(bit_pooled_mean)

    w_z = np.array([0.5, 0.5, 0.5])
    elig_a = np.array([True, True, True])
    q = np.zeros(3)
    rand = np.zeros(3)
    hv = np.zeros(3)
    shuf = np.zeros(3)
    elig_b = np.array([True, True, True])

    res = decide(w_p2, w_z, elig_a, q, rand, hv, shuf, elig_b, [], [])

    delta = w_p2 - w_z
    expected_a2 = e5stats.to_unit(delta)
    np.testing.assert_allclose(res["inputs"]["A2"], expected_a2)
    np.testing.assert_allclose(res["inputs"]["A1_lower"], w_z)
    np.testing.assert_allclose(res["inputs"]["A1_upper"], 1.0 - w_z)
    expected_log_k = float(e5stats.betting_logk(expected_a2, e5stats.to_unit(e5stats.DELTA_MIN), n_plan=400))
    assert res["log_k"]["A2"] == pytest.approx(expected_log_k)


def test_decide_both_claims_hold():
    n = 400
    w_p2 = np.full(n, 1.0)
    w_z = np.full(n, 0.5)
    elig_a = np.ones(n, dtype=bool)
    q = np.full(n, 1.0)
    rand = np.zeros(n)
    hv = np.zeros(n)
    shuf = np.zeros(n)
    elig_b = np.ones(n, dtype=bool)

    res = decide(w_p2, w_z, elig_a, q, rand, hv, shuf, elig_b, [], [])

    assert res["outcomes"]["A"] == "holds"
    assert res["outcomes"]["B"] == "holds"


def test_decide_n_a_below_400_uses_only_eligible_pairs_and_n_plan_400():
    rng = np.random.default_rng(3)
    w_p2 = rng.random(10)
    w_z = rng.random(10)
    elig_a = np.array([True, False, True, False, True, False, False, True, False, False])
    q, rand, hv, shuf = rng.random(10), rng.random(10), rng.random(10), rng.random(10)
    elig_b = elig_a.copy()

    res = decide(w_p2, w_z, elig_a, q, rand, hv, shuf, elig_b, [], [])

    assert res["n_a"] == int(elig_a.sum()) == 4
    w_z_e = w_z[elig_a]
    np.testing.assert_allclose(res["inputs"]["A1_lower"], w_z_e)
    expected_log_k = float(e5stats.betting_logk(w_z_e, 0.5 - e5stats.EPSILON, n_plan=400))
    assert res["log_k"]["A1_lower"] == pytest.approx(expected_log_k)
    # n_plan is fixed at 400, not the realized eligible count (4): the two give different capital.
    wrong_n_plan = float(e5stats.betting_logk(w_z_e, 0.5 - e5stats.EPSILON, n_plan=4))
    assert res["log_k"]["A1_lower"] != pytest.approx(wrong_n_plan)


def test_decide_outcomes_invalid_and_not_estimable():
    w_p2 = np.array([0.9, 0.9])
    w_z = np.array([0.5, 0.5])
    elig_a = np.array([False, False])  # no eligible A pair
    q = np.array([0.5, 0.5])
    rand = np.array([0.0, 0.0])
    hv = np.array([0.0, 0.0])
    shuf = np.array([0.0, 0.0])
    elig_b = np.array([True, True])

    res = decide(w_p2, w_z, elig_a, q, rand, hv, shuf, elig_b, [], ["head_hash_mismatch"])

    assert res["outcomes"]["A"] == "not_estimable"
    assert res["outcomes"]["B"] == "invalid"


def test_bootstrap_percentile_seed0_degenerate_flag():
    res = bootstrap(np.array([0.5, 0.5, 0.5]))
    assert res["n"] == 3
    assert res["mean"] == pytest.approx(0.5)
    assert res["degenerate"] is True  # every resample mean is exactly 0.5

    res2 = bootstrap(np.array([0.0, 1.0, np.nan]))
    assert res2["n"] == 2  # NaN dropped before resampling
    assert res2["degenerate"] is False
