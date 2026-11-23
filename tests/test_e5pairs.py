import numpy as np

from ncm_sudoku.e5pairs import PAIR_SEEDS, contrast_stats, generate_pair, generate_pairs
from ncm_sudoku.solve import count_solutions
from ncm_sudoku.subsets import SEEDS


def test_namespaces_do_not_collide_with_subsets():
    assert not set(PAIR_SEEDS.values()) & set(SEEDS.values())


def test_pair_members_share_solution_and_clue_count():
    p = generate_pair(PAIR_SEEDS["pairs_probe_train"], 0)
    for g in (p.a, p.b):
        assert (g > 0).sum() == 30
        assert count_solutions(g, limit=2) == 1
        assert np.array_equal(g[g > 0], p.solution[g > 0])
    assert not np.array_equal(p.a > 0, p.b > 0)
    assert p.pair_id == f"e5pair-v1-{PAIR_SEEDS['pairs_probe_train']}-0"


def test_generation_is_deterministic():
    p, q = generate_pair(8, 3), generate_pair(8, 3)
    assert np.array_equal(p.a, q.a) and np.array_equal(p.b, q.b) and np.array_equal(p.solution, q.solution)


def test_contrast_stats_on_a_few_pairs():
    pairs = generate_pairs("pairs_probe_val", 3)
    st = contrast_stats(pairs)
    assert 0 <= st["shared_clues"]["min"] <= st["shared_clues"]["max"] < 30
    assert st["both_empty_cells_with_different_mask"]["max"] <= st["cells_empty_in_both"]["max"]
