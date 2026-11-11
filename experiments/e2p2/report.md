# E2 pilot-2 report

**Non-confirmatory pilot (plan v3.6 §12.1).** These numbers plan the confirmatory study; they are not evidence for H2 or H3.

- CAL puzzles: 300; run time 3.91 h
- θ₂ (frequency): -0.0894, 95% bootstrap [-0.1174, -0.0627], n=300; family 0.98333 bootstrap [-0.1237, -0.0579]
- θ_comp (frequency): 0.0074, 95% bootstrap [-0.0111, 0.0263], n=300; family 0.98333 bootstrap [-0.0162, 0.0307]
- θ₂′ (frequency): 0.0011, 95% bound [-0.0303, 0.0303], n=300; TOST90 bound [-0.0303, 0.0303]
- Equivalence (TOST, θ₂′ frequency inside ±0.03): False
- Sham mismatch (puzzles whose sham solve differs from A; nonzero = instrumentation error): B1≠A 0; L2 0, L6 0, L11 0

| AUC pair | AUC A | AUC B | range | reason |
|---|---|---|---|---|
| 6-11 | -0.0071 | 0.0000 | [0.000, 0.000] | – |
| 2-11 | – | – | [0.000, 0.000] | no positive-width common range |

| Config | Excluded | Solve A | Solve B | Solve C | Solve D | Median TV |
|---|---|---|---|---|---|---|
| L2/frequency/d1 | 0.000 | 0.850 | 0.850 | 0.850 | 0.851 | 0.000 |
| L2/frequency/d2 | 0.000 | 0.850 | 0.850 | 0.850 | 0.853 | 0.000 |
| L2/uniform/d1 | 0.000 | 0.850 | 0.850 | 0.844 | 0.840 | 0.000 |
| L2/uniform/d2 | 0.000 | 0.850 | 0.850 | 0.844 | 0.838 | 0.000 |
| L6/frequency/d1 | 0.000 | 0.850 | 0.850 | 0.850 | 0.854 | 0.000 |
| L6/frequency/d2 | 0.000 | 0.850 | 0.850 | 0.850 | 0.854 | 0.000 |
| L6/frequency/d4 | 0.000 | 0.850 | 0.850 | 0.850 | 0.850 | 0.000 |
| L6/frequency/d8 | 0.000 | 0.850 | 0.850 | 0.850 | 0.839 | 0.000 |
| L6/frequency/d13 | 0.000 | 0.850 | 0.850 | 0.850 | 0.840 | 0.000 |
| L6/uniform/d1 | 0.000 | 0.850 | 0.850 | 0.850 | 0.849 | 0.000 |
| L6/uniform/d2 | 0.000 | 0.850 | 0.850 | 0.850 | 0.857 | 0.000 |
| L6/uniform/d4 | 0.000 | 0.850 | 0.850 | 0.850 | 0.842 | 0.000 |
| L6/uniform/d8 | 0.000 | 0.850 | 0.850 | 0.850 | 0.843 | 0.000 |
| L6/uniform/d13 | 0.000 | 0.850 | 0.850 | 0.850 | 0.839 | 0.000 |
| L11/frequency/d1 | 0.000 | 0.850 | 0.850 | 0.850 | 0.850 | 0.000 |
| L11/frequency/d4 | 0.000 | 0.850 | 0.850 | 0.848 | 0.850 | 0.000 |
| L11/frequency/d11 | 0.000 | 0.850 | 0.850 | 0.844 | 0.844 | 0.000 |
| L11/frequency/d21 | 0.000 | 0.850 | 0.850 | 0.838 | 0.841 | 0.000 |
| L11/frequency/d41 | 0.000 | 0.850 | 0.850 | 0.821 | 0.834 | 0.000 |
| L11/frequency/d67 | 0.000 | 0.850 | 0.850 | 0.799 | 0.812 | 0.001 |
| L11/uniform/d1 | 0.000 | 0.850 | 0.850 | 0.850 | 0.850 | 0.000 |
| L11/uniform/d4 | 0.000 | 0.850 | 0.850 | 0.847 | 0.848 | 0.000 |
| L11/uniform/d11 | 0.000 | 0.850 | 0.850 | 0.843 | 0.847 | 0.000 |
| L11/uniform/d21 | 0.000 | 0.850 | 0.850 | 0.837 | 0.843 | 0.000 |
| L11/uniform/d41 | 0.000 | 0.850 | 0.850 | 0.831 | 0.831 | 0.000 |
| L11/uniform/d67 | 0.000 | 0.850 | 0.850 | 0.814 | 0.828 | 0.000 |
