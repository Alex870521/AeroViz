"""Per-bin ``dlogDp`` widths, and the total-concentration bug they fix.

Until 2026-09-09 both size-distribution readers computed the total number
concentration as ``sum(dN/dlogDp) * np.diff(np.log(dp)).mean()`` — a natural
log where the data is per *decade*, and a single mean step where the grid may
not be uniform. The natural log alone inflated every total by ``ln(10)``,
which silently moved the `Invalid Number Conc` thresholds:
``MAX_TOTAL_CONC`` of 1e7 behaved as 4.34e6 (SMPS) and 700 behaved as 304
(APS, where it was rejecting valid scans).

Nothing tested the total, which is why it survived. These tests pin it.
"""
import numpy as np
import pytest

from AeroViz.dataProcess.SizeDistr._size_dist import bin_widths


def _log_grid(start, ratio, n):
    return start * ratio ** np.arange(n)


class TestBinWidths:
    def test_uniform_grid_matches_channel_spacing(self):
        """A 64-channels-per-decade SMPS grid gives 1/64 in every bin."""
        dp = _log_grid(11.8, 10 ** (1 / 64), 110)
        w = bin_widths(dp)
        assert w.shape == dp.shape
        assert np.allclose(w, 1 / 64, rtol=1e-6)

    def test_hybrid_grid_gets_two_widths(self):
        """The point of per-bin: a grid whose spacing changes partway.

        A single mean step would hand both halves the same width, over-counting
        the fine half and under-counting the coarse one.
        """
        fine = _log_grid(11.8, 10 ** (1 / 64), 100)      # SMPS-like
        coarse = _log_grid(600.0, 10 ** (1 / 16), 30)    # APS-like
        dp = np.concatenate([fine, coarse])
        w = bin_widths(dp)

        # Away from the junction each half keeps its own spacing.
        assert np.allclose(w[:90], 1 / 64, rtol=1e-3)
        assert np.allclose(w[-25:], 1 / 16, rtol=1e-3)

        single_mean = np.diff(np.log10(dp)).mean()
        assert single_mean > 1.4 * (1 / 64)   # would over-count the fine half
        assert single_mean < 0.7 * (1 / 16)   # and under-count the coarse half

    def test_widths_tile_the_range_without_gaps_or_overlap(self):
        """Widths sum to the full log10 span covered by the bin edges."""
        dp = _log_grid(11.8, 10 ** (1 / 64), 110)
        w = bin_widths(dp)
        span = np.log10(dp[-1] * np.sqrt(dp[-1] / dp[-2])) - np.log10(dp[0] * np.sqrt(dp[0] / dp[1]))
        assert w.sum() == pytest.approx(span, rel=1e-10)

    @pytest.mark.parametrize('n', [0, 1])
    def test_degenerate_grid_falls_back(self, n):
        """Fewer than two bins carry no spacing information."""
        w = bin_widths(np.array([100.0] * n))
        assert w.shape == (n,)
        assert np.all(w == 0.014) if n else True


class TestTotalConcentration:
    """``sum(dN/dlogDp x dlogDp)`` must recover the number concentration."""

    def test_recovers_a_known_total(self):
        dp = _log_grid(11.8, 10 ** (1 / 64), 110)
        w = bin_widths(dp)
        # A log-normal in number: N=1e4 /cm3, GMD 60 nm, GSD 1.8
        n_total, gmd, gsd = 1e4, 60.0, 1.8
        dndlogdp = (n_total / (np.sqrt(2 * np.pi) * np.log10(gsd))
                    * np.exp(-(np.log10(dp) - np.log10(gmd)) ** 2
                             / (2 * np.log10(gsd) ** 2)))
        assert (dndlogdp * w).sum() == pytest.approx(n_total, rel=0.01)

    def test_natural_log_would_inflate_by_ln10(self):
        """Regression: the exact shape of the bug that was fixed."""
        dp = _log_grid(11.8, 10 ** (1 / 64), 110)
        dndlogdp = np.full(dp.size, 1000.0)

        correct = (dndlogdp * bin_widths(dp)).sum()
        buggy = dndlogdp.sum() * np.diff(np.log(dp[:-1])).mean()

        assert buggy / correct == pytest.approx(np.log(10), rel=0.02)
