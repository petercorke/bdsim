# Golden-master references

One `.npz` archive per example: the numbers the example produces, as written by
`--npz`, without wall time or solver counts. `tests/test_golden.py` runs each example
and compares.

Read one with `np.load("eg1.npz", allow_pickle=False)`.

To regenerate after a change that is **meant** to alter the numbers:

    pytest tests/test_golden.py --update-golden

then say in the commit message why they changed. These tests show that results are
unchanged, not that they are correct.
