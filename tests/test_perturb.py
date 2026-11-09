import torch

from ncm_sudoku.perturb import code_frequencies, dose_grid, perturb_level

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
