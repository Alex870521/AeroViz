"""
Core class for particle size distribution data.

This module provides the SizeDist class, which encapsulates particle
size distribution data and provides convenient properties for accessing
particle diameters, logarithmic bin widths, and distribution state information.
"""

from typing import Literal

import numpy as np
from pandas import DataFrame

__all__ = ['SizeDist', 'get_required_format']


class SizeDist:
    """
    A class representing particle size distribution data.

    This class encapsulates particle size distribution data and provides
    convenient properties for accessing particle diameters, logarithmic
    bin widths, and distribution state information.

    Attributes
    ----------
    _data : DataFrame
        The processed PSD data stored as a pandas DataFrame.
    _dp : ndarray
        The array of particle diameters from the PSD data.
    _dlogdp : ndarray
        The array of logarithmic particle diameter bin widths.
    _index : DatetimeIndex
        The index of the DataFrame representing time.
    _state : str
        The state of particle size distribution data ('dN', 'ddp', 'dlogdp').
    _weighting : str
        The weighting type for distribution calculations.

    Methods
    -------
    data
        Returns the size distribution DataFrame.
    dp
        Returns the particle diameter array.
    dlogdp
        Returns the logarithmic bin width array.
    index
        Returns the time index.
    state
        Returns the distribution state.
    weighting
        Returns the weighting type.

    Examples
    --------
    >>> from pandas import read_csv
    >>> df = read_csv('PNSD_dNdlogdp.csv', parse_dates=['Time'], index_col='Time')
    >>> psd = SizeDist(df, state='dlogdp', weighting='n')
    >>> print(psd.dp)
    """

    def __init__(self,
                 data: DataFrame,
                 state: Literal['dN', 'ddp', 'dlogdp'] = 'dlogdp',
                 weighting: Literal['n', 's', 'v', 'ext_in', 'ext_ex'] = 'n'
                 ):
        """
        Initialize a SizeDist object.

        Parameters
        ----------
        data : DataFrame
            The particle size distribution data with particle diameters as columns.
            Column names must be numeric diameter values in nm.
        state : {'dN', 'ddp', 'dlogdp'}, default='dlogdp'
            The state of the distribution data:
            - 'dN': Raw number concentration
            - 'ddp': dN/ddp normalized
            - 'dlogdp': dN/dlogdp normalized
        weighting : {'n', 's', 'v', 'ext_in', 'ext_ex'}, default='n'
            The weighting type for property calculations:
            - 'n': Number weighting
            - 's': Surface weighting
            - 'v': Volume weighting
            - 'ext_in': Internal extinction weighting
            - 'ext_ex': External extinction weighting

        Raises
        ------
        ValueError
            If data is None or empty, or column names are not numeric.
        TypeError
            If data is not a DataFrame.
        """
        # Validate input data
        if data is None:
            raise ValueError(
                "\nSizeDist 需要 DataFrame 資料！\n"
                "  格式要求: 欄位名稱為粒徑值 (nm)\n"
                "  例如: df.columns = [10.0, 20.0, 50.0, ...]"
            )
        if not isinstance(data, DataFrame):
            raise TypeError(
                f"\nSizeDist 需要 pandas DataFrame！\n"
                f"  收到類型: {type(data).__name__}"
            )
        if data.empty:
            raise ValueError(
                "\nSizeDist 收到空的 DataFrame！\n"
                "  請確認資料已正確讀取"
            )

        # Validate column names are numeric (particle diameters)
        try:
            _ = np.array(data.columns, dtype=float)
        except (ValueError, TypeError):
            raise ValueError(
                f"\nSizeDist 欄位名稱必須為數值 (粒徑 nm)！\n"
                f"  收到欄位: {list(data.columns[:5])}{'...' if len(data.columns) > 5 else ''}\n"
                f"  正確格式: [10.0, 20.0, 50.0, 100.0, ...]"
            )

        # Validate state parameter
        if state not in ['dN', 'dlogdp', 'ddp']:
            raise ValueError(
                f"\nSizeDist 無效的 state 參數！\n"
                f"  收到: '{state}'\n"
                f"  有效選項: ['dN', 'ddp', 'dlogdp']"
            )

        # Validate weighting parameter
        if weighting not in ['n', 's', 'v', 'ext_in', 'ext_ex']:
            raise ValueError(
                f"\nSizeDist 無效的 weighting 參數！\n"
                f"  收到: '{weighting}'\n"
                f"  有效選項: ['n', 's', 'v', 'ext_in', 'ext_ex']"
            )

        self._data = data
        self._dp = np.array(self._data.columns, dtype=float)
        self._dlogdp = np.full_like(self._dp, 0.014)
        self._index = self._data.index.copy()
        self._state = state
        self._weighting = weighting

    @property
    def data(self) -> DataFrame:
        """Return the size distribution DataFrame."""
        return self._data

    @property
    def dp(self) -> np.ndarray:
        """Return the particle diameter array in nm."""
        return self._dp

    @dp.setter
    def dp(self, new_dp: np.ndarray):
        """Set the particle diameter array."""
        self._dp = new_dp

    @property
    def dlogdp(self) -> np.ndarray:
        """Return the logarithmic bin width array."""
        return self._dlogdp

    @dlogdp.setter
    def dlogdp(self, new_dlogdp: np.ndarray):
        """Set the logarithmic bin width array."""
        self._dlogdp = new_dlogdp

    @property
    def index(self):
        """Return the time index of the distribution data."""
        return self._index

    @property
    def state(self):
        """Return the distribution state."""
        return self._state

    @state.setter
    def state(self, value):
        """Set the distribution state."""
        if value not in ['dN', 'dlogdp', 'ddp']:
            raise ValueError("state must be 'dN', 'dlogdp', or 'ddp'")
        self._state = value

    @property
    def weighting(self):
        """Return the weighting type."""
        return self._weighting

    @weighting.setter
    def weighting(self, value):
        """Set the weighting type."""
        if value not in ['n', 's', 'v', 'ext_in', 'ext_ex']:
            raise ValueError("weighting must be 'n', 's', 'v', 'ext_in', or 'ext_ex'")
        self._weighting = value

    # =========================================================================
    # Distribution Calculations
    # =========================================================================

    def to_surface(self) -> DataFrame:
        """
        Convert to surface area distribution.

        Formula: dS/dlogDp = π * dp² * dN/dlogDp

        Returns
        -------
        DataFrame
            Surface area distribution (nm² / cm³).

        Examples
        --------
        >>> psd = SizeDist(df)
        >>> surface = psd.to_surface()
        """
        return self._data.dropna().apply(
            lambda col: np.pi * self._dp ** 2 * np.array(col),
            axis=1, result_type='broadcast'
        ).reindex(self._index)

    def to_volume(self) -> DataFrame:
        """
        Convert to volume distribution.

        Formula: dV/dlogDp = (π/6) * dp³ * dN/dlogDp

        Returns
        -------
        DataFrame
            Volume distribution (nm³ / cm³).

        Examples
        --------
        >>> psd = SizeDist(df)
        >>> volume = psd.to_volume()
        """
        return self._data.dropna().apply(
            lambda col: np.pi / 6 * self._dp ** 3 * np.array(col),
            axis=1, result_type='broadcast'
        ).reindex(self._index)

    def properties(self) -> DataFrame:
        """
        Calculate statistical properties of the distribution.

        Returns
        -------
        DataFrame
            Properties including GMD, GSD, mode, and mode contributions.

        Examples
        --------
        >>> psd = SizeDist(df)
        >>> props = psd.properties()
        """
        from functools import partial
        from .prop import properties as calc_props

        return self._data.dropna().apply(
            partial(calc_props, dp=self._dp, dlogdp=self._dlogdp, weighting=self._weighting),
            axis=1, result_type='expand'
        ).reindex(self._index)

    def to_extinction(self,
                      RI: DataFrame,
                      method: str = 'internal',
                      result_type: str = 'extinction') -> DataFrame:
        """
        Calculate extinction distribution using Mie theory.

        Parameters
        ----------
        RI : DataFrame
            Refractive index data with n and k columns.
        method : {'internal', 'external', 'core_shell', 'sensitivity'}, default='internal'
            Mixing method for Mie calculation.
        result_type : {'extinction', 'scattering', 'absorption'}, default='extinction'
            Type of optical result.

        Returns
        -------
        DataFrame
            Extinction distribution (Mm⁻¹).

        Examples
        --------
        >>> psd = SizeDist(df)
        >>> ext = psd.to_extinction(df_RI, method='internal')
        """
        from functools import partial
        from pandas import concat
        from ..Optical.mie_theory import internal, external, core_shell, sensitivity

        method_mapping = {
            'internal': internal,
            'external': external,
            'core_shell': core_shell,
            'sensitivity': sensitivity
        }

        if RI is None or (hasattr(RI, 'empty') and RI.empty):
            raise ValueError(
                "\nto_extinction() 需要折射率資料！\n"
                "  必要輸入: RI (DataFrame)\n"
                "  需包含欄位: n (real), k (imaginary)"
            )

        if method not in method_mapping:
            raise ValueError(
                f"\n無效的計算方法: '{method}'\n"
                f"  有效方法: {list(method_mapping.keys())}"
            )

        mie_func = method_mapping[method]
        combined = concat([self._data, RI], axis=1).dropna()

        return combined.apply(
            partial(mie_func, dp=self._dp, result_type=result_type),
            axis=1, result_type='expand'
        ).reindex(self._index).set_axis(self._dp, axis=1)

    def mode_statistics(self, unit: str = 'nm') -> dict:
        """
        Calculate statistics for different size modes.

        Computes number, surface, and volume distributions along with
        GMD, GSD, total, and mode for each size range.

        Parameters
        ----------
        unit : {'nm', 'um'}, default='nm'
            Unit of particle diameter in the data.

        Returns
        -------
        dict
            - 'number': Number distribution (dN)
            - 'number_norm': Normalized number distribution (dN/dlogDp)
            - 'surface': Surface area distribution
            - 'surface_norm': Normalized surface distribution
            - 'volume': Volume distribution
            - 'volume_norm': Normalized volume distribution
            - 'statistics': DataFrame with GMD, GSD, total, mode per size mode

        Examples
        --------
        >>> psd = SizeDist(df)
        >>> stats = psd.mode_statistics()
        >>> stats['statistics']  # GMD, GSD for each mode
        """
        # Size mode boundaries in nm
        mode_bounds = {
            'Nucleation': (10, 25),
            'Aitken': (25, 100),
            'Accumulation': (100, 1000),
            'Coarse': (1000, 2500),
        }

        # Prepare distributions
        number_norm = self._data
        number = (self._data * self._dlogdp).copy()
        surface_norm = self.to_surface()
        surface = (surface_norm * self._dlogdp).copy()
        volume_norm = self.to_volume()
        volume = (volume_norm * self._dlogdp).copy()

        out = {
            'number': number,
            'number_norm': number_norm,
            'surface': surface,
            'surface_norm': surface_norm,
            'volume': volume,
            'volume_norm': volume_norm,
        }

        # Calculate statistics for each mode
        df_stats = DataFrame(index=self._index)

        bounds = [('all', (self._dp.min(), self._dp.max() + 1))]
        for mode_name, (lb, ub) in mode_bounds.items():
            if unit == 'um':
                lb, ub = lb / 1e3, ub / 1e3
            bounds.append((mode_name, (lb, ub)))

        dist_types = [
            ('num', number),
            ('surf', surface),
            ('vol', volume)
        ]

        for type_name, dist_data in dist_types:
            for mode_name, (lb, ub) in bounds:
                mode_dp = self._dp[(self._dp >= lb) & (self._dp < ub)]
                if not mode_dp.any():
                    continue

                mode_dist = dist_data[mode_dp].copy()

                # Calculate GMD, GSD, total
                total, gmd, gsd = _geometric_statistics(mode_dp, mode_dist)

                df_stats[f'total_{type_name}_{mode_name}'] = total
                df_stats[f'GMD_{type_name}_{mode_name}'] = gmd
                df_stats[f'GSD_{type_name}_{mode_name}'] = gsd

                # Calculate mode (peak diameter)
                mask = mode_dist.notna().any(axis=1)
                df_stats.loc[mask, f'mode_{type_name}_{mode_name}'] = mode_dist.loc[mask].idxmax(axis=1)
                df_stats.loc[~mask, f'mode_{type_name}_{mode_name}'] = np.nan

        out['statistics'] = df_stats

        return out

    def to_dry(self, df_gRH: DataFrame, uniform: bool = True) -> DataFrame:
        """
        Convert ambient (wet) PSD to dry PSD.

        Shrinks particles according to hygroscopic growth factor and
        redistributes concentrations to appropriate smaller diameter bins.

        Parameters
        ----------
        df_gRH : DataFrame
            DataFrame with 'gRH' column (growth factor = Dp_wet / Dp_dry).
        uniform : bool, default=True
            If True, apply uniform gRH across all sizes.
            If False, apply size-dependent gRH based on lognormal distribution.

        Returns
        -------
        DataFrame
            Dry particle size distribution.

        Examples
        --------
        >>> psd = SizeDist(df_pnsd)
        >>> dry_psd = psd.to_dry(df_chem[['gRH']])
        """
        from pandas import concat

        if df_gRH is None or (hasattr(df_gRH, 'empty') and df_gRH.empty):
            raise ValueError(
                "\nto_dry() 需要成長因子資料！\n"
                "  必要輸入: df_gRH (DataFrame)\n"
                "  需包含欄位: gRH (Dp_wet / Dp_dry)"
            )

        if 'gRH' not in df_gRH.columns:
            raise ValueError(
                f"\nto_dry() 需要 'gRH' 欄位！\n"
                f"  收到欄位: {list(df_gRH.columns)}"
            )

        combined = concat([self._data, df_gRH[['gRH']]], axis=1).dropna()

        if combined.empty:
            return DataFrame(columns=self._dp, index=self._index)

        result = combined.apply(
            lambda row: _dry_pnsd_process(
                row[self._data.columns].values,
                self._dp,
                row['gRH'],
                uniform=uniform
            ),
            axis=1,
            result_type='expand'
        )

        if len(result.columns) < len(self._dp):
            result = result.reindex(columns=range(len(self._dp)))

        result.columns = self._dp[:len(result.columns)]

        return result.reindex(self._index)

    def lung_deposition(self, activity: str = 'light') -> dict:
        """
        Calculate lung deposition using ICRP 66 model.

        Based on the ICRP (International Commission on Radiological Protection)
        Human Respiratory Tract Model for particle deposition.

        Parameters
        ----------
        activity : {'sleep', 'sitting', 'light', 'heavy'}, default='light'
            Activity level affecting breathing pattern:
            - 'sleep': Sleeping (nasal, 7.5 L/min)
            - 'sitting': Sitting awake (nasal, 9 L/min)
            - 'light': Light exercise (nasal+oral, 25 L/min)
            - 'heavy': Heavy exercise (oral, 50 L/min)

        Returns
        -------
        dict
            - 'DF': Deposition fraction DataFrame (HA, TB, AL, Total)
            - 'deposited': Deposited number distribution
            - 'dose': Regional deposited dose (particles/cm³)
            - 'total_dose': Total deposited particles

        Notes
        -----
        Deposition regions:
        - HA (Head Airways): 頭部氣道 (鼻、咽、喉)
        - TB (Tracheobronchial): 氣管支氣管區
        - AL (Alveolar): 肺泡區

        References
        ----------
        - ICRP Publication 66 (1994)
        - Hinds, W.C. (1999) Aerosol Technology

        Examples
        --------
        >>> psd = SizeDist(df)
        >>> lung = psd.lung_deposition(activity='light')
        >>> lung['DF']        # Deposition fractions
        >>> lung['dose']      # Regional dose
        """
        # Deposition fraction functions based on ICRP 66 / Hinds (1999)
        dp_um = self._dp / 1000  # Convert nm to μm

        # Calculate deposition fractions for each region
        DF_HA, DF_TB, DF_AL = _calc_deposition_fractions(dp_um, activity)
        DF_total = DF_HA + DF_TB + DF_AL

        # Create deposition fraction DataFrame
        df_DF = DataFrame({
            'HA': DF_HA,
            'TB': DF_TB,
            'AL': DF_AL,
            'Total': DF_total
        }, index=self._dp)

        # Calculate deposited distribution for each time point
        deposited_HA = self._data.dropna().apply(
            lambda row: np.array(row) * DF_HA, axis=1, result_type='broadcast'
        ).reindex(self._index)

        deposited_TB = self._data.dropna().apply(
            lambda row: np.array(row) * DF_TB, axis=1, result_type='broadcast'
        ).reindex(self._index)

        deposited_AL = self._data.dropna().apply(
            lambda row: np.array(row) * DF_AL, axis=1, result_type='broadcast'
        ).reindex(self._index)

        deposited_total = self._data.dropna().apply(
            lambda row: np.array(row) * DF_total, axis=1, result_type='broadcast'
        ).reindex(self._index)

        # Calculate total dose (integrated over size)
        dlogdp = self._dlogdp[0] if len(self._dlogdp) > 0 else 0.014

        dose_HA = deposited_HA.sum(axis=1) * dlogdp
        dose_TB = deposited_TB.sum(axis=1) * dlogdp
        dose_AL = deposited_AL.sum(axis=1) * dlogdp
        dose_total = deposited_total.sum(axis=1) * dlogdp

        from pandas import concat
        dose = concat([dose_HA, dose_TB, dose_AL, dose_total], axis=1)
        dose.columns = ['HA', 'TB', 'AL', 'Total']

        return {
            'DF': df_DF,
            'deposited': {
                'HA': deposited_HA,
                'TB': deposited_TB,
                'AL': deposited_AL,
                'Total': deposited_total
            },
            'dose': dose,
            'total_dose': dose_total
        }


def _calc_deposition_fractions(dp_um: np.ndarray, activity: str = 'light') -> tuple:
    """
    Calculate regional deposition fractions based on ICRP 66 model.

    Parameters
    ----------
    dp_um : np.ndarray
        Particle diameter in micrometers.
    activity : str
        Activity level.

    Returns
    -------
    tuple
        (DF_HA, DF_TB, DF_AL) deposition fractions.
    """
    # Breathing parameters by activity level
    # (nasal fraction, tidal volume L, breathing frequency /min)
    activity_params = {
        'sleep': (1.0, 0.625, 12),    # 7.5 L/min, nasal
        'sitting': (1.0, 0.75, 12),   # 9 L/min, nasal
        'light': (0.5, 1.25, 20),     # 25 L/min, mixed
        'heavy': (0.0, 1.92, 26),     # 50 L/min, oral
    }

    if activity not in activity_params:
        raise ValueError(f"Invalid activity: {activity}. Choose from {list(activity_params.keys())}")

    f_nasal, Vt, f_breath = activity_params[activity]

    # Inhalability (fraction that enters the respiratory system)
    # Based on ICRP 66
    IF = 1 - 0.5 * (1 - 1 / (1 + 0.00076 * dp_um ** 2.8))

    # Head Airways (HA) deposition - empirical fit
    # Nasal deposition
    DF_HA_nasal = IF * (1 / (1 + np.exp(6.84 + 1.183 * np.log(dp_um))) +
                        1 / (1 + np.exp(0.924 - 1.885 * np.log(dp_um))))

    # Oral deposition (lower for larger particles)
    DF_HA_oral = IF * (1 / (1 + np.exp(6.84 + 1.183 * np.log(dp_um))) * 0.5)

    # Weighted HA deposition
    DF_HA = f_nasal * DF_HA_nasal + (1 - f_nasal) * DF_HA_oral

    # Fraction reaching thoracic region
    F_thoracic = IF - DF_HA

    # Tracheobronchial (TB) deposition
    # Based on impaction and sedimentation
    DF_TB = F_thoracic * (0.00352 / dp_um * (np.exp(-0.234 * (np.log(dp_um) + 3.40) ** 2) +
                                              63.9 * np.exp(-0.819 * (np.log(dp_um) - 1.61) ** 2)))

    # Ensure non-negative
    DF_TB = np.maximum(DF_TB, 0)

    # Alveolar (AL) deposition
    # Diffusion-dominated for ultrafine, sedimentation for larger
    F_alveolar = F_thoracic - DF_TB

    DF_AL = F_alveolar * (0.0155 / dp_um * (np.exp(-0.416 * (np.log(dp_um) + 2.84) ** 2) +
                                             19.11 * np.exp(-0.482 * (np.log(dp_um) - 1.362) ** 2)))

    # Ensure non-negative and bounded
    DF_AL = np.maximum(DF_AL, 0)
    DF_AL = np.minimum(DF_AL, F_alveolar)

    # Ensure total doesn't exceed IF
    DF_total = DF_HA + DF_TB + DF_AL
    scale = np.where(DF_total > IF, IF / DF_total, 1.0)
    DF_HA *= scale
    DF_TB *= scale
    DF_AL *= scale

    return DF_HA, DF_TB, DF_AL


def _resolved_gRH(dp: np.ndarray, gRH: float = 1.31, uniform: bool = True) -> np.ndarray:
    """
    Calculate the growth factor for each particle diameter bin.

    Parameters
    ----------
    dp : np.ndarray
        Array of particle diameters in nm.
    gRH : float, default=1.31
        The uniform growth factor to apply if uniform=True.
    uniform : bool, default=True
        If True, apply uniform gRH across all sizes.
        If False, apply size-dependent gRH based on lognormal distribution.

    Returns
    -------
    np.ndarray
        Growth factor for each diameter bin.
    """
    if uniform:
        return np.full(dp.size, gRH)
    else:
        def lognorm_dist(x, geoMean, geoStd):
            return (gRH / (np.log10(geoStd) * np.sqrt(2 * np.pi))) * np.exp(
                -(x - np.log10(geoMean)) ** 2 / (2 * np.log10(geoStd) ** 2))

        result = lognorm_dist(np.log10(dp), 200, 2.0)
        return np.where(result < 1, 1, result)


def _dry_pnsd_process(dist: np.ndarray,
                      dp: np.ndarray,
                      gRH: float,
                      uniform: bool = True) -> np.ndarray:
    """
    Convert ambient PSD to dry PSD by shrinking particles.

    Parameters
    ----------
    dist : np.ndarray
        The ambient particle number distribution.
    dp : np.ndarray
        Array of particle diameters in nm.
    gRH : float
        The growth factor (Dp_wet / Dp_dry).
    uniform : bool, default=True
        If True, apply uniform gRH across all sizes.

    Returns
    -------
    np.ndarray
        The dry particle number distribution.
    """
    ndp = np.array(dist[:np.size(dp)])
    growth_factors = _resolved_gRH(dp, gRH, uniform=uniform)

    # Calculate dry diameters
    dry_dp = dp / growth_factors

    # Find which bin each dry diameter belongs to
    belong_which_ibin = np.digitize(dry_dp, dp) - 1

    # Redistribute particles to appropriate bins
    result = {}
    for i, (ibin, dn) in enumerate(zip(belong_which_ibin, ndp)):
        if ibin < 0 or ibin >= len(dp):
            continue
        if dp[ibin] not in result:
            result[dp[ibin]] = []
        result[dp[ibin]].append(ndp[i])

    # Average concentrations in each bin
    dry_ndp = []
    for key in sorted(result.keys()):
        val = result[key]
        dry_ndp.append(sum(val) / len(val))

    return np.array(dry_ndp)


def _geometric_statistics(dp: np.ndarray, dist: DataFrame) -> tuple:
    """
    Calculate geometric mean diameter and standard deviation.

    Parameters
    ----------
    dp : ndarray
        Particle diameters.
    dist : DataFrame
        Distribution data.

    Returns
    -------
    tuple
        (total, GMD, GSD)
    """
    total = dist.sum(axis=1)
    total = total.where(total > 0).copy()

    log_dp = np.log(dp)
    gmd = ((dist * log_dp).sum(axis=1)) / total

    dp_mesh, gmd_mesh = np.meshgrid(log_dp, gmd)
    gsd = ((((dp_mesh - gmd_mesh) ** 2) * dist).sum(axis=1) / total) ** 0.5

    return total, gmd.apply(np.exp), gsd.apply(np.exp)


def get_required_format():
    """
    Get required format for SizeDist input data.

    Returns
    -------
    dict
        Dictionary describing the required format for SizeDist.

    Examples
    --------
    >>> fmt = get_required_format()
    >>> print(fmt['data'])
    """
    return {
        'data': {
            'type': 'pandas DataFrame',
            'columns': '粒徑值作為欄位名稱 (nm)，例如: 10.0, 20.0, 50.0, ...',
            'values': '各粒徑的數目濃度 (dN/dlogDp 或 dN/ddp 或 dN)',
            'index': 'DatetimeIndex (時間索引)'
        },
        'state': {
            'options': ['dN', 'ddp', 'dlogdp'],
            'default': 'dlogdp',
            'description': {
                'dN': '原始數目濃度',
                'ddp': 'dN/ddp 正規化',
                'dlogdp': 'dN/dlogDp 正規化'
            }
        },
        'weighting': {
            'options': ['n', 's', 'v', 'ext_in', 'ext_ex'],
            'default': 'n',
            'description': {
                'n': 'Number weighting 數目加權',
                's': 'Surface weighting 表面積加權',
                'v': 'Volume weighting 體積加權',
                'ext_in': 'Internal extinction weighting 內混合消光加權',
                'ext_ex': 'External extinction weighting 外混合消光加權'
            }
        },
        'usage_example': "psd = SizeDist(df, state='dlogdp', weighting='n')"
    }
