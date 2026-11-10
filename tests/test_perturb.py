import torch

from ncm_sudoku.perturb import (
    DOSE_FRACTIONS_V35,
    DOSE_FRACTIONS_V36,
    code_frequencies,
    dose_grid,
    level1_weights,
    perturb_level,
    run_seed,
)

LEVELS = (1, 2, 4, 6, 9, 13, 18, 26, 37, 50, 67, 89)


def test_dose_grid():
    assert dose_grid(1) == [1]
    assert dose_grid(2) == [1]
    assert dose_grid(13) == [1, 2, 4]
    assert dose_grid(67) == [1, 4, 11, 21]


def test_code_frequencies_sum_to_one():
    codes = torch.randint(0, 16, (5, 322), generator=torch.Generator().manual_seed(0))
    freqs = code_frequencies(codes, LEVELS)
    assert len(freqs) == 12
    assert all(abs(float(f.sum()) - 1.0) < 1e-6 and f.shape == (16,) for f in freqs)


def test_frequency_excludes_original():
    level = torch.full((1000, 6), 3, dtype=torch.long)
    freqs = torch.zeros(16)
    freqs[3], freqs[7], freqs[9] = 0.5, 0.3, 0.2
    new, eligible = perturb_level(level, 1, "frequency", freqs, torch.Generator().manual_seed(1))
    assert eligible.all()
    changed = new[new != 3]
    assert len(changed) == 1000
    assert set(changed.tolist()) <= {7, 9}


def test_ineligible_when_no_alternative():
    level = torch.full((4, 6), 3, dtype=torch.long)
    freqs = torch.zeros(16)
    freqs[3] = 1.0
    new, eligible = perturb_level(level, 2, "frequency", freqs, torch.Generator().manual_seed(1))
    assert not eligible.any()
    assert torch.equal(new, level)


def test_uniform_changes_exactly_dose_positions():
    level = torch.randint(0, 16, (50, 13), generator=torch.Generator().manual_seed(2))
    new, eligible = perturb_level(level, 4, "uniform", torch.full((16,), 1 / 16), torch.Generator().manual_seed(3))
    assert eligible.all()
    assert ((new != level).sum(dim=1) == 4).all()


def test_perturb_deterministic_given_seed():
    level = torch.randint(0, 16, (10, 13), generator=torch.Generator().manual_seed(2))
    freqs = torch.full((16,), 1 / 16)
    a, _ = perturb_level(level, 2, "frequency", freqs, torch.Generator().manual_seed(5))
    b, _ = perturb_level(level, 2, "frequency", freqs, torch.Generator().manual_seed(5))
    assert torch.equal(a, b)


def test_input_not_mutated():
    level = torch.randint(0, 16, (10, 13), generator=torch.Generator().manual_seed(2))
    copy = level.clone()
    perturb_level(level, 2, "uniform", torch.full((16,), 1 / 16), torch.Generator().manual_seed(5))
    assert torch.equal(level, copy)


def test_dose_grid_v36():
    assert dose_grid(2, DOSE_FRACTIONS_V36) == [1, 2]
    assert dose_grid(13, DOSE_FRACTIONS_V36) == [1, 2, 4, 8, 13]
    assert dose_grid(67, DOSE_FRACTIONS_V36) == [1, 4, 11, 21, 41, 67]
    assert dose_grid(67) == [1, 4, 11, 21]          # pilot-1 default unchanged


def test_run_seed_collision_free():
    keys = [(lv, p, d, s) for lv in (1, 2, 6, 11, 12) for p in ("frequency", "uniform")
            for d in range(1, 90) for s in range(20)]
    assert len({run_seed(*k) for k in keys}) == len(keys)
    assert run_seed(11, "frequency", 1, 0) == run_seed(11, "frequency", 1, 0)


def test_level1_weights_frequency():
    f = torch.zeros(16); f[0], f[1], f[2] = 0.5, 0.3, 0.2
    w = level1_weights(torch.tensor([0, 3]), f, "frequency")
    assert torch.allclose(w[0], torch.tensor([0, .6, .4] + [0] * 13, dtype=torch.double))
    assert torch.allclose(w[1], torch.tensor([.5, .3, .2] + [0] * 13, dtype=torch.double))


def test_level1_weights_uniform():
    w = level1_weights(torch.tensor([5]), torch.ones(16) / 16, "uniform")
    assert w[0, 5] == 0 and torch.allclose(w[0].sum(), torch.tensor(1.0, dtype=torch.double))
    assert torch.allclose(w[0][w[0] > 0], torch.full((15,), 1 / 15, dtype=torch.double))


def test_level1_weights_ineligible_when_only_original_has_mass():
    f = torch.zeros(16); f[7] = 1.0
    w = level1_weights(torch.tensor([7]), f, "frequency")
    assert torch.equal(w, torch.zeros(1, 16, dtype=torch.double))


def test_full_dose_frequency_ineligible_row():
    f = torch.zeros(16); f[3] = 1.0
    codes = torch.tensor([[3, 3, 3], [1, 2, 4]])
    new, eligible = perturb_level(codes, 3, "frequency", f, torch.Generator().manual_seed(0))
    assert eligible.tolist() == [False, True]
    assert torch.equal(new[0], codes[0]) and (new[1] == 3).all()
