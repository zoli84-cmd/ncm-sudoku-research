import numpy as np
import pytest
import torch

from conftest import needs_model


@pytest.mark.slow
@needs_model
def test_capture_pass_keeps_codes_and_extracts_consistent_arrays(model, released):
    from ncm_sudoku.e5extract import LEVEL7_PASS, extract_batch, generate_capture_pass
    from ncm_sudoku.runner import generate_codes, puzzle_tensor

    puzzles, solutions = released[0][:2], released[1][:2]
    plain = generate_codes(model, puzzles, batch_size=2)
    codes, layers = generate_capture_pass(model.net, puzzle_tensor(puzzles))
    assert torch.equal(plain, codes)
    P = model.net.prefix_len
    assert len(layers) == len(model.net.transformer.blocks) + 1
    assert layers[0].shape[1] == P + model.levels[LEVEL7_PASS]

    out = extract_batch(model, puzzles, solutions)
    assert out["prefix_cells"].shape == (2, 9, 81, model.net.config.n_embd)
    assert out["prefix_bos"].shape == (2, 9, model.net.config.n_embd)
    assert out["level7_queries"].shape[2] == model.levels[LEVEL7_PASS]
    assert out["z6"].shape == (2, 81, 256) and out["z6_teacher"].shape == (2, 81, 256)
    assert out["solved"].dtype == bool
    assert np.array_equal(out["codes"], plain.numpy().astype(np.int8))


class _FakeNet(torch.nn.Module):
    """Minimal stand-in for the upstream generator: 7 passes, each running every block
    and then a code head whose argmax is the generated code (as upstream greedy decoding)."""

    def __init__(self):
        super().__init__()
        torch.manual_seed(0)
        self.transformer = torch.nn.Module()
        self.transformer.blocks = torch.nn.ModuleList([torch.nn.Linear(4, 4) for _ in range(8)])
        self.lm_heads = torch.nn.ModuleList([torch.nn.Linear(4, 3) for _ in range(7)])

    def generate(self, idx, x, **kw):
        codes = []
        for p in range(7):
            h = x.float() + p
            for b in self.transformer.blocks:
                h = b(h)
            codes.append(self.lm_heads[p](h).argmax(-1))
        return torch.cat(codes, dim=1)


def _plain_codes(net, x):
    with torch.no_grad():
        return net.generate(None, x)


def test_generation_finiteness_hooks_keep_codes_and_raise_on_nan():
    from ncm_sudoku.e5extract import generate_capture_pass
    from ncm_sudoku.e5test import NonFiniteError

    net, x = _FakeNet(), torch.arange(24.0).reshape(2, 3, 4) / 10
    codes, layers = generate_capture_pass(net, x)
    assert torch.equal(codes, _plain_codes(net, x)) and len(layers) == 9
    assert all(not m._forward_hooks and not m._forward_pre_hooks for m in net.modules())

    with torch.no_grad():
        net.transformer.blocks[3].bias[0] = float("nan")
    with pytest.raises(NonFiniteError, match="block output"):
        generate_capture_pass(net, x)
    assert all(not m._forward_hooks and not m._forward_pre_hooks for m in net.modules())

    net = _FakeNet()
    with torch.no_grad():
        net.lm_heads[2].bias[1] = float("inf")
    with pytest.raises(NonFiniteError, match="code logits"):
        generate_capture_pass(net, x)
