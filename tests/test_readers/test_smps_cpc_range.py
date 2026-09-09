"""The `CPC Over-range` rule: a bin above what the counter can actually count.

The rated maximum of a CPC applies to the concentration it sees at one DMA
voltage — the narrow mobility band the column is passing at that instant — not
to the integrated total of the whole distribution. Comparing it against the
total is a category error that makes the check either useless (a 3788's 4e5
implies a total far beyond anything ambient) or wrong.

These tests pin the conversion and the model lookup. They deliberately avoid
fixture data: the arithmetic is what regresses, and it is checkable in closed
form.
"""
import numpy as np
import pytest

from AeroViz.rawDataReader.script.SMPS import Reader as SMPSReader


class TestRatedMaxLookup:
    """The model field is free text — `3772`, `3788 Low Flow`, `3022A`."""

    @pytest.mark.parametrize('model,expected', [
        ('3772', 1e4),
        ('3788 Low Flow', 4.0e5),
        ('3787 Low Flow', 2.5e5),
        ('3022 Low Flow', 1.0e7),
    ])
    def test_matches_substring(self, model, expected):
        assert SMPSReader._rated_max_conc(model) == expected

    def test_longest_key_wins(self):
        """`3022A` must not be answered by the `3022` entry."""
        assert '3022' in SMPSReader.CPC_MAX_CONC and '3022A' in SMPSReader.CPC_MAX_CONC
        assert SMPSReader._rated_max_conc('3022A') == SMPSReader.CPC_MAX_CONC['3022A']

    @pytest.mark.parametrize('model', ['', None, '3750', 'unknown counter'])
    def test_unknown_model_returns_none(self, model):
        """Unknown counters leave the rule inert rather than guessing."""
        assert SMPSReader._rated_max_conc(model) is None


class TestBinCeiling:
    DP = np.array([12.0, 50.0, 200.0, 594.0])

    def _ceiling(self, beta=0.25, cpc_max=1e4):
        return SMPSReader._cpc_bin_ceiling(SMPSReader, self.DP, beta, cpc_max)

    def test_ceiling_falls_with_diameter(self):
        """|dlnZ/dlnDp| runs ~2 (free molecular) to ~1 (continuum), so the
        transfer function widens with size and the ceiling drops."""
        c = self._ceiling()
        assert np.all(np.diff(c) < 0)
        assert c[0] / c[-1] == pytest.approx(1.6, rel=0.15)

    def test_narrower_transfer_function_raises_the_ceiling(self):
        """A higher sheath ratio (smaller beta) means the counter sees a
        thinner slice, so it tolerates a denser aerosol."""
        assert np.all(self._ceiling(beta=0.15) > self._ceiling(beta=0.25))

    def test_scales_linearly_with_the_rated_maximum(self):
        assert np.allclose(self._ceiling(cpc_max=4e5), 40 * self._ceiling(cpc_max=1e4))

    def test_per_scan_beta_gives_one_row_each(self):
        beta = np.array([0.25, 0.15, 0.25])
        c = SMPSReader._cpc_bin_ceiling(SMPSReader, self.DP, beta, 1e4)
        assert c.shape == (3, self.DP.size)
        assert np.all(c[1] > c[0])           # the 0.15 scan tolerates more

    def test_a_3772_ceiling_is_far_below_the_old_total_threshold(self):
        """Why the old `MAX_TOTAL_CONC` never fired: a per-bin ceiling for the
        smallest counter is ~1e5, three orders below the 1e7 it was compared to."""
        assert self._ceiling().max() < 2e5


class TestPlausibilityBounds:
    def test_minimum_admits_a_clean_background_site(self):
        """EBAS background stations sit at 50-300 /cm3; a minimum of 2000
        rejected 99-100% of their record."""
        assert SMPSReader.MIN_TOTAL_CONC < 50

    def test_maximum_stays_above_any_credible_ambient_total(self):
        """Roadside peaks reach 2-5e5, so the backstop must sit above that
        while still being tight enough to mean something."""
        assert 5e5 < SMPSReader.MAX_TOTAL_CONC <= 1e6
