import copy
import json
import re
from pathlib import Path

import pytest

from ncm_sudoku import wp4numbers
from ncm_sudoku.wp4numbers import KEYS, collect, fmt, load_sources, lookup, numbers_json, numbers_tex

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def sources():
    return load_sources(ROOT)


def test_fmt_kinds():
    assert fmt(-0.1112751815580535, "pp1") == r"\ensuremath{-}11.1"
    assert fmt(0.0028915830506550293, "dec4") == "0.0029"
    assert fmt(8.651136464594964e-05, "sig2") == "0.000087"
    assert fmt(0.8766666666666667, "pct1") == "87.7"
    assert fmt(0.9833333333333333, "dec2") == "98.33"
    assert fmt(600, "int") == "600"
    assert fmt(0.01, "g") == "0.01" and fmt(0.0116, "g") == "0.0116"


def test_fmt_sig2_keeps_two_significant_digits_for_large_and_negative_values():
    assert fmt(0.0505651, "sig2") == "0.051"
    assert fmt(-0.00012796667615799141, "sig2") == r"\ensuremath{-}0.00013"


def test_fmt_negative_zero_after_rounding_has_no_sign():
    assert fmt(-0.00001, "dec4") == "0.0000"


def test_fmt_rejects_none_and_nan():
    with pytest.raises(ValueError):
        fmt(None, "dec4")
    with pytest.raises(ValueError):
        fmt(float("nan"), "dec4")
    with pytest.raises(ValueError):
        fmt(1.0, "nope")


def test_lookup_names_missing_path():
    with pytest.raises(KeyError, match=r"primary\.H9\.estimate"):
        lookup({"primary": {"H1": {}}}, "primary.H9.estimate")


def test_lookup_indexes_lists_and_selects_rows():
    doc = {"a": [{"row": "x", "v": 1}, {"row": "y", "v": 2}], "b": [5, 6]}
    assert lookup(doc, "b.1") == 6
    assert lookup(doc, "a[row=y].v") == 2
    with pytest.raises(KeyError, match=r"a\[row=z\]"):
        lookup(doc, "a[row=z].v")


def test_collect_real_results_primary_values(sources):
    nums = collect(sources)
    assert nums["h1.est"] == "0.0029" and nums["h1.fam.lo"] == "0.0025" and nums["h1.fam.hi"] == "0.0033"
    assert nums["h2.est"] == r"\ensuremath{-}11.1" and nums["h3.fam.lo"] == "0.1"
    assert nums["n.test"] == "600" and nums["plan.h1margin"] == "0.01"
    assert nums["level.family"] == "98.33" and nums["level.tost"] == "96.67"
    assert nums["e1.solve"] == "87.7" and nums["g0.official"] == "86.3"
    assert nums["brier.teacher.L06"] == "0.2307" and nums["rawgen.proj.est"] == r"\ensuremath{-}0.2292"
    assert set(nums) == set(KEYS)


def test_collect_none_interval_raises_naming_the_key(sources):
    broken = copy.deepcopy(sources)
    broken["results"]["primary"]["H3"]["family"] = None
    with pytest.raises((KeyError, ValueError), match=r"primary\.H3\.family"):
        collect(broken)


def test_numbers_tex_defines_lookup_macro_and_every_key(sources):
    nums = collect(sources)
    tex = numbers_tex(nums)
    assert r"\PackageError{wp4}{Unknown result key #1}" in tex
    defined = re.findall(r"^\\wpdef\{([^}]*)\}\{(.*)\}$", tex, flags=re.M)
    assert dict(defined) == nums


def test_numbers_json_sorted_and_round_trips(sources):
    nums = collect(sources)
    text = numbers_json(nums)
    assert text.endswith("\n") and json.loads(text) == nums
    assert list(json.loads(text)) == sorted(nums)


def test_plan_constants_match_the_plan():
    assert wp4numbers.H2_PRACTICAL == 0.05 and wp4numbers.H3_PRACTICAL == 0.03


def test_plan_constants_equal_wp2eval():
    from ncm_sudoku import wp2eval

    for name in ("H1_MARGIN", "THETA2P_MARGIN", "THETA_T_MARGIN", "EQUIV_TOLERANCE"):
        assert getattr(wp4numbers, name) == getattr(wp2eval, name), name
