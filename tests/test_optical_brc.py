"""Tests for Brown Carbon (BrC) optical separation algorithm."""
import numpy as np
import pandas as pd
import pytest

from AeroViz.dataProcess.Optical._derived import calculate_BrC_absorption


class TestBrCAbsorption:
    """Test cases for BrC absorption calculation."""

    @pytest.fixture
    def sample_absorption_data(self):
        """Create sample multi-wavelength absorption data similar to AE33 output."""
        np.random.seed(42)
        n_samples = 100

        # Base absorption at 880nm (reference, pure BC)
        abs_880 = np.random.uniform(5, 50, n_samples)

        wavelengths = [370, 470, 520, 590, 660, 880, 950]

        data = {}
        for wl in wavelengths:
            # BC component
            abs_bc = abs_880 * (880 / wl) ** 1.0

            # Add BrC enhancement at shorter wavelengths (stronger at UV)
            if wl < 880:
                brc_factor = ((880 - wl) / 500) ** 1.5
                abs_brc = abs_880 * brc_factor * np.random.uniform(0.1, 0.5, n_samples)
                data[f'abs_{wl}'] = abs_bc + abs_brc
            else:
                data[f'abs_{wl}'] = abs_bc

        index = pd.date_range('2024-01-01', periods=n_samples, freq='h')
        return pd.DataFrame(data, index=index)

    @pytest.fixture
    def pure_bc_data(self):
        """Create data for pure BC (no BrC) with AAE=1."""
        n_samples = 50
        abs_880 = np.linspace(10, 100, n_samples)

        wavelengths = [370, 470, 520, 590, 660, 880, 950]
        data = {}
        for wl in wavelengths:
            data[f'abs_{wl}'] = abs_880 * (880 / wl) ** 1.0

        index = pd.date_range('2024-01-01', periods=n_samples, freq='h')
        return pd.DataFrame(data, index=index)

    def test_basic_calculation(self, sample_absorption_data):
        """Test basic BrC calculation returns expected columns."""
        result = calculate_BrC_absorption(sample_absorption_data)

        expected_wavelengths = [370, 470, 520, 590, 660]
        for wl in expected_wavelengths:
            assert f'abs_BC_{wl}' in result.columns
            assert f'abs_BrC_{wl}' in result.columns
            assert f'BrC_fraction_{wl}' in result.columns

        assert 'AAE_BrC' in result.columns

    def test_brc_non_negative(self, sample_absorption_data):
        """Test that valid BrC absorption is always non-negative."""
        result = calculate_BrC_absorption(sample_absorption_data)

        for col in result.columns:
            if col.startswith('abs_BrC_'):
                valid_values = result[col].dropna()
                assert (valid_values >= 0).all(), f"{col} has negative values"

    def test_brc_fraction_range(self, sample_absorption_data):
        """Test that BrC fraction is between 0 and 1."""
        result = calculate_BrC_absorption(sample_absorption_data)

        for col in result.columns:
            if col.startswith('BrC_fraction_'):
                valid_values = result[col].dropna()
                assert (valid_values >= 0).all(), f"{col} has values < 0"
                assert (valid_values <= 1).all(), f"{col} has values > 1"

    def test_pure_bc_has_zero_brc(self, pure_bc_data):
        """Test that pure BC data (AAE=1) gives zero or near-zero BrC."""
        result = calculate_BrC_absorption(pure_bc_data, aae_bc=1.0)

        # For pure BC with AAE=1, BrC should be essentially zero
        for col in result.columns:
            if col.startswith('abs_BrC_'):
                valid_values = result[col].dropna()
                if len(valid_values) > 0:
                    assert (valid_values < 1e-10).all(), f"{col} should be ~0 for pure BC"

    def test_bc_calculation_formula(self, sample_absorption_data):
        """Test that BC is calculated correctly using the power law."""
        ref_wl = 880
        aae_bc = 1.0
        result = calculate_BrC_absorption(
            sample_absorption_data,
            ref_wavelength=ref_wl,
            aae_bc=aae_bc
        )

        # Only check valid rows (where BC doesn't exceed total)
        valid_mask = result['abs_BC_370'].notna()

        abs_ref = sample_absorption_data.loc[valid_mask, f'abs_{ref_wl}']
        expected_bc_370 = abs_ref * (ref_wl / 370) ** aae_bc

        np.testing.assert_array_almost_equal(
            result.loc[valid_mask, 'abs_BC_370'].values,
            expected_bc_370.values,
            decimal=10
        )

    def test_brc_equals_total_minus_bc_for_valid(self, sample_absorption_data):
        """Test that BrC = Total - BC for valid separations."""
        result = calculate_BrC_absorption(sample_absorption_data)

        for wl in [370, 470, 520, 590, 660]:
            # Only check rows where BrC is not NaN (valid separation)
            valid_mask = result[f'abs_BrC_{wl}'].notna()

            total = sample_absorption_data.loc[valid_mask, f'abs_{wl}']
            bc = result.loc[valid_mask, f'abs_BC_{wl}']
            brc = result.loc[valid_mask, f'abs_BrC_{wl}']

            expected_brc = (total - bc).clip(lower=0)
            np.testing.assert_array_almost_equal(
                brc.values,
                expected_brc.values,
                decimal=10
            )

    def test_custom_aae_bc(self, sample_absorption_data):
        """Test calculation with custom AAE_BC values."""
        result_aae1 = calculate_BrC_absorption(sample_absorption_data, aae_bc=1.0)
        result_aae11 = calculate_BrC_absorption(sample_absorption_data, aae_bc=1.1)

        # Only compare valid rows in both results
        valid_mask = result_aae1['abs_BC_370'].notna() & result_aae11['abs_BC_370'].notna()

        # With higher AAE_BC, BC absorption is higher
        assert (result_aae11.loc[valid_mask, 'abs_BC_370'] >= result_aae1.loc[valid_mask, 'abs_BC_370']).all()

    def test_custom_wavelengths(self, sample_absorption_data):
        """Test calculation with custom wavelength selection."""
        custom_wavelengths = [370, 470]
        result = calculate_BrC_absorption(
            sample_absorption_data,
            wavelengths=custom_wavelengths
        )

        assert 'abs_BrC_370' in result.columns
        assert 'abs_BrC_470' in result.columns
        assert 'abs_BrC_520' not in result.columns
        assert 'abs_BrC_590' not in result.columns

    def test_custom_reference_wavelength(self, sample_absorption_data):
        """Test calculation with custom reference wavelength."""
        result = calculate_BrC_absorption(
            sample_absorption_data,
            ref_wavelength=950,
            wavelengths=[370, 470, 520, 590, 660, 880]
        )

        # Only check valid rows
        valid_mask = result['abs_BC_370'].notna()

        abs_ref = sample_absorption_data.loc[valid_mask, 'abs_950']
        expected_bc_370 = abs_ref * (950 / 370) ** 1.0
        np.testing.assert_array_almost_equal(
            result.loc[valid_mask, 'abs_BC_370'].values,
            expected_bc_370.values,
            decimal=10
        )

    def test_missing_reference_wavelength(self):
        """Test error when reference wavelength is not available."""
        data = pd.DataFrame({
            'abs_370': [10, 20, 30],
            'abs_470': [8, 16, 24],
        })

        with pytest.raises(ValueError, match="找不到參考波長"):
            calculate_BrC_absorption(data, ref_wavelength=880)

    def test_empty_dataframe(self):
        """Test error handling for empty DataFrame."""
        empty_df = pd.DataFrame()

        with pytest.raises(ValueError, match="需要多波長吸收係數資料"):
            calculate_BrC_absorption(empty_df)

    def test_none_input(self):
        """Test error handling for None input."""
        with pytest.raises(ValueError, match="需要多波長吸收係數資料"):
            calculate_BrC_absorption(None)

    def test_aae_brc_calculation(self, sample_absorption_data):
        """Test that AAE_BrC is calculated and reasonable."""
        result = calculate_BrC_absorption(sample_absorption_data)

        assert 'AAE_BrC' in result.columns

        # Valid AAE_BrC should exist for some rows
        valid_aae = result['AAE_BrC'].dropna()
        assert len(valid_aae) > 0, "Should have some valid AAE_BrC values"

    def test_preserves_index(self, sample_absorption_data):
        """Test that output preserves input index."""
        result = calculate_BrC_absorption(sample_absorption_data)
        pd.testing.assert_index_equal(result.index, sample_absorption_data.index)

    def test_handles_nan_values(self):
        """Test that NaN values are handled correctly."""
        data = pd.DataFrame({
            'abs_370': [10, np.nan, 30, 40],
            'abs_470': [8, 16, np.nan, 32],
            'abs_520': [7, 14, 21, np.nan],
            'abs_590': [6, 12, 18, 24],
            'abs_660': [5, 10, 15, 20],
            'abs_880': [4, 8, 12, 16],
        })

        result = calculate_BrC_absorption(data)
        assert len(result) == 4

    def test_bc_exceeds_total_gives_nan(self):
        """Test that BC > total at any wavelength makes entire row NaN."""
        # Create data where BC will exceed total at 370nm
        # abs_BC_370 = abs_880 * (880/370)^1 = abs_880 * 2.378
        # If abs_370 < abs_880 * 2.378, BC > total
        data = pd.DataFrame({
            'abs_370': [10.0, 50.0],  # First row: BC will exceed total
            'abs_470': [15.0, 40.0],
            'abs_520': [18.0, 35.0],
            'abs_590': [20.0, 30.0],
            'abs_660': [22.0, 28.0],
            'abs_880': [25.0, 20.0],  # First row: BC_370 = 25 * 2.378 = 59.5 > 10
        })

        result = calculate_BrC_absorption(data)

        # First row should be invalid (all values NaN, including BC)
        assert np.isnan(result.loc[0, 'abs_BC_370'])
        assert np.isnan(result.loc[0, 'abs_BrC_370'])
        assert np.isnan(result.loc[0, 'AAE_BrC'])

        # Second row should be valid
        assert not np.isnan(result.loc[1, 'abs_BC_370'])
        assert not np.isnan(result.loc[1, 'abs_BrC_370'])


class TestBrCWithOpticalClass:
    """Test BrC calculation through the Optical class interface."""

    def test_optical_class_brc_method(self):
        """Test that Optical.BrC method works correctly."""
        from AeroViz.dataProcess.Optical import Optical

        np.random.seed(42)
        n_samples = 20
        abs_880 = np.random.uniform(10, 50, n_samples)

        wavelengths = [370, 470, 520, 590, 660, 880, 950]
        data = {}
        for wl in wavelengths:
            abs_bc = abs_880 * (880 / wl) ** 1.0
            if wl < 880:
                brc_enhancement = abs_880 * 0.2 * (880 - wl) / 500
                data[f'abs_{wl}'] = abs_bc + brc_enhancement
            else:
                data[f'abs_{wl}'] = abs_bc

        df_abs = pd.DataFrame(data, index=pd.date_range('2024-01-01', periods=n_samples, freq='h'))

        optical = Optical()
        result = optical.BrC(df_abs)

        assert 'abs_BrC_370' in result.columns
        assert 'AAE_BrC' in result.columns
        assert len(result) == n_samples


class TestBrCEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_single_row(self):
        """Test with single row of data."""
        data = pd.DataFrame({
            'abs_370': [20.0],
            'abs_470': [15.0],
            'abs_520': [12.0],
            'abs_590': [10.0],
            'abs_660': [8.0],
            'abs_880': [5.0],
        }, index=[pd.Timestamp('2024-01-01')])

        result = calculate_BrC_absorption(data)

        assert len(result) == 1
        assert 'abs_BrC_370' in result.columns

    def test_very_small_absorption(self):
        """Test with very small absorption values."""
        data = pd.DataFrame({
            'abs_370': [0.001, 0.002],
            'abs_470': [0.0008, 0.0016],
            'abs_520': [0.0007, 0.0014],
            'abs_590': [0.0006, 0.0012],
            'abs_660': [0.0005, 0.0010],
            'abs_880': [0.0004, 0.0008],
        })

        result = calculate_BrC_absorption(data)
        assert len(result) == 2

    def test_zero_absorption(self):
        """Test behavior with zero absorption values."""
        data = pd.DataFrame({
            'abs_370': [0, 10],
            'abs_470': [0, 8],
            'abs_520': [0, 7],
            'abs_590': [0, 6],
            'abs_660': [0, 5],
            'abs_880': [0, 4],
        })

        result = calculate_BrC_absorption(data)
        assert len(result) == 2

    def test_wavelength_order_independence(self):
        """Test that column order doesn't affect results."""
        data1 = pd.DataFrame({
            'abs_370': [20.0],
            'abs_470': [15.0],
            'abs_880': [5.0],
        })

        data2 = pd.DataFrame({
            'abs_880': [5.0],
            'abs_470': [15.0],
            'abs_370': [20.0],
        })

        result1 = calculate_BrC_absorption(data1, wavelengths=[370, 470])
        result2 = calculate_BrC_absorption(data2, wavelengths=[370, 470])

        np.testing.assert_array_almost_equal(
            result1['abs_BC_370'].values,
            result2['abs_BC_370'].values
        )

    def test_negative_brc_at_one_wavelength_invalidates_row(self):
        """Test that if BC > total at ANY wavelength, entire row is NaN."""
        # BC_660 = 10 * (880/660)^1 = 13.33, which is > abs_660=12
        data = pd.DataFrame({
            'abs_370': [50.0],
            'abs_470': [40.0],
            'abs_520': [30.0],
            'abs_590': [20.0],
            'abs_660': [12.0],  # BC will exceed this
            'abs_880': [10.0],
        })

        result = calculate_BrC_absorption(data)

        # All values should be NaN (including BC)
        assert np.isnan(result.loc[0, 'abs_BC_370'])
        assert np.isnan(result.loc[0, 'abs_BC_660'])
        assert np.isnan(result.loc[0, 'abs_BrC_370'])
        assert np.isnan(result.loc[0, 'abs_BrC_660'])
        assert np.isnan(result.loc[0, 'AAE_BrC'])
