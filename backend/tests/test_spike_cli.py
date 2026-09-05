"""Guards on the bench CLI's destructive flag.

`--save-memory` calls `save_store`, which overwrites. A run that is not the full k=0 baseline
would replace the store with a partial or few-shot-assisted one, and every later sweep arm reads
it — so the contamination is silent and shows up only as an unexplained k-curve.
"""
from __future__ import annotations

import pytest

from spike.__main__ import main


class TestSaveMemoryGuards:
    def test_save_memory_rejects_k_above_zero(self, capsys):
        with pytest.raises(SystemExit):
            main(["--save-memory", "--k", "3"])
        assert "--k 0" in capsys.readouterr().err

    def test_save_memory_rejects_a_case_subset(self, capsys):
        with pytest.raises(SystemExit):
            main(["--save-memory", "--case", "product__combo"])
        assert "full corpus" in capsys.readouterr().err

    def test_save_memory_at_k_zero_is_allowed_past_the_guard(self, capsys):
        """The guard must not block the one run that is supposed to seed the store. It gets
        past argument validation and fails later, for a different reason — asserted, so this
        cannot start passing because the guard widened."""
        with pytest.raises(SystemExit):
            main(["--save-memory", "--k", "0", "--fixtures", "does/not/exist"])
        err = capsys.readouterr().err
        assert "is not a directory" in err
        # argparse echoes the flag list in its usage line, so match the guard's own wording.
        assert "requires --k 0" not in err
        assert "requires the full corpus" not in err
