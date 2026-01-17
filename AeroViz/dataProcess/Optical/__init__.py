from ..core import Writer, run_process, deprecated

__all__ = ['Optical']


class Optical(Writer):

    @run_process('Optical - scaCoe', 'scaCoe')
    @deprecated(
        "This method is now automatically called during file reading. Please update your code to use the pre-calculated values.")
    def scaCoe(self, df_sca, instru, specified_band):
        from .coefficient import _scaCoe

        out = _scaCoe(df_sca, instru=instru, specified_band=[550] if specified_band is None else specified_band)

        return self, out

    @run_process('Optical - absCoe', 'absCoe')
    @deprecated(
        "This method is now automatically called during file reading. Please update your code to use the pre-calculated values.")
    def absCoe(self, df_ae33, instru, specified_band):
        from .coefficient import _absCoe

        out = _absCoe(df_ae33, instru=instru, specified_band=[550] if specified_band is None else specified_band)

        return self, out

    @run_process('Optical - basic', 'opt_basic')
    def basic(self, df_sca, df_abs, df_mass=None, df_no2=None, df_temp=None):
        from ._extinction import _basic

        out = _basic(df_sca, df_abs, df_mass, df_no2, df_temp)

        return self, out

    @run_process('Optical - Mie', 'Mie')
    def Mie(self, df_psd, df_m, wavelength=550, psd_type='auto'):
        """
        Calculate optical properties from PSD using Mie theory.

        Parameters
        ----------
        df_psd : DataFrame
            Particle number size distribution.
            Columns are particle diameters (nm), rows are time points.
        df_m : DataFrame or Series
            Complex refractive index (n + ik) for each time point.
        wavelength : float, default=550
            Wavelength of incident light in nm.
        psd_type : str, default='auto'
            Type of PSD input:
            - 'dNdlogDp': Number concentration per log bin width (#/cm³)
            - 'dN': Number concentration per bin (#/cm³/bin)
            - 'auto': Auto-detect with warning if uncertain

        Returns
        -------
        DataFrame
            Optical coefficients with columns: ext, sca, abs (Mm⁻¹)
        """
        from ._mie_sd import Mie_SD

        # Get valid indices (where both PSD and RI have data)
        original_index = df_psd.index.copy()
        valid_index = df_psd.loc[df_m.dropna().index].dropna(how='all').index

        # Calculate Mie for valid data only
        psd_valid = df_psd.loc[valid_index]
        ri_valid = df_m.loc[valid_index]

        result = Mie_SD(ri_valid.values, wavelength, psd_valid, psd_type=psd_type)

        # Reindex to original index (NaN for missing)
        out = result.reindex(original_index)

        return self, out

    @run_process('Optical - IMPROVE', 'IMPROVE')
    def IMPROVE(self, df_mass, df_RH=None, method='revised', df_nh4_status=None):
        """
        Calculate extinction using IMPROVE equation.

        Parameters
        ----------
        df_mass : DataFrame
            Mass concentrations with columns: AS, AN, OM, Soil, SS, EC
        df_RH : DataFrame, optional
            Relative humidity data
        method : str, default='revised'
            IMPROVE version: 'revised' or 'modified'
        df_nh4_status : DataFrame, optional
            NH4 status from reconstruction_basic()['NH4_status'].
            If provided, rows with 'Deficiency' status will be excluded.

        Returns
        -------
        dict
            Dictionary with keys:
            - 'dry': Dry extinction DataFrame
            - 'wet': Wet extinction DataFrame (if df_RH provided)
            - 'ALWC': Water contribution (wet - dry)
            - 'fRH': Hygroscopic growth factor
        """
        from ._IMPROVE import revised, modified

        if method == 'revised':
            out = revised(df_mass, df_RH, df_nh4_status)
        elif method == 'modified':
            out = modified(df_mass, df_RH, df_nh4_status)
        else:
            raise ValueError(f"method must be 'revised' or 'modified', got '{method}'")

        return self, out

    @run_process('Optical - gas_extinction', 'gas_ext')
    def gas_extinction(self, df_no2, df_temp):
        """
        Calculate gas contribution to extinction.

        Parameters
        ----------
        df_no2 : DataFrame
            NO2 concentration (ppb)
        df_temp : DataFrame
            Ambient temperature (Celsius)

        Returns
        -------
        DataFrame
            Gas extinction with ScatteringByGas, AbsorptionByGas, ExtinctionByGas
        """
        from ._IMPROVE import gas_extinction as calc_gas_ext

        out = calc_gas_ext(df_no2, df_temp)

        return self, out

    @run_process('Optical - retrieve_RI', 'retrieve_RI')
    def retrieve_RI(self, df_optical, df_pnsd, dlogdp=0.014, wavelength=550):
        """
        Retrieve refractive index from optical and PSD measurements.

        Parameters
        ----------
        df_optical : DataFrame
            Optical data with Extinction, Scattering, Absorption columns
        df_pnsd : DataFrame
            Particle number size distribution data
        dlogdp : float, default=0.014
            Logarithmic bin width
        wavelength : float, default=550
            Wavelength in nm

        Returns
        -------
        DataFrame
            Retrieved refractive index with re_real and re_imaginary columns
        """
        from ._retrieve_RI import retrieve_RI

        out = retrieve_RI(df_optical, df_pnsd, dlogdp, wavelength)

        return self, out

    @run_process('Optical - derived', 'derived')
    def derived(self, df_sca=None, df_abs=None, df_ext=None, df_no2=None, df_o3=None,
                df_ec=None, df_oc=None, df_pm1=None, df_pm25=None, df_improve=None):
        """
        Calculate derived optical and atmospheric parameters.

        Parameters
        ----------
        df_sca : DataFrame, optional
            Scattering coefficient (Mm-1)
        df_abs : DataFrame, optional
            Absorption coefficient (Mm-1)
        df_ext : DataFrame, optional
            Extinction coefficient (Mm-1)
        df_no2 : DataFrame, optional
            NO2 concentration (ppb)
        df_o3 : DataFrame, optional
            O3 concentration (ppb)
        df_ec : DataFrame, optional
            Elemental carbon (ug/m3)
        df_oc : DataFrame, optional
            Organic carbon (ug/m3)
        df_pm1 : DataFrame, optional
            PM1 (ug/m3)
        df_pm25 : DataFrame, optional
            PM2.5 (ug/m3)
        df_improve : DataFrame, optional
            IMPROVE extinction data

        Returns
        -------
        DataFrame
            Derived parameters (PG, MAC, Ox, Vis_cal, fRH_IMPR, OCEC_ratio, etc.)
        """
        from ._derived import derived_parameters

        out = derived_parameters(
            df_sca=df_sca, df_abs=df_abs, df_ext=df_ext,
            df_no2=df_no2, df_o3=df_o3, df_ec=df_ec, df_oc=df_oc,
            df_pm1=df_pm1, df_pm25=df_pm25, df_improve=df_improve
        )

        return self, out

    @run_process('Optical - BrC', 'BrC')
    def BrC(self, df_abs, wavelengths=None, ref_wavelength=880, aae_bc=1.0):
        """
        Calculate Brown Carbon (BrC) absorption by separating BC and BrC contributions.

        This method uses the AAE-based separation approach:
        1. Assume Black Carbon (BC) has AAE = 1.0 (or user-specified value)
        2. Absorption at 880nm is entirely from BC (reference wavelength)
        3. Calculate BC absorption at shorter wavelengths using power law
        4. BrC absorption = Total absorption - BC absorption
        5. Calculate BrC AAE from the derived spectrum

        Parameters
        ----------
        df_abs : DataFrame
            Absorption coefficient data with columns like 'abs_370', 'abs_470',
            'abs_520', 'abs_590', 'abs_660', 'abs_880'.
            Units should be Mm-1.
        wavelengths : list[int], optional
            Wavelengths to calculate BrC absorption for.
            Default: [370, 470, 520, 590, 660]
        ref_wavelength : int, default=880
            Reference wavelength (nm) assumed to be purely BC absorption.
        aae_bc : float, default=1.0
            Absorption Ångström Exponent for Black Carbon.
            Typical range: 0.8-1.1 for fresh BC.

        Returns
        -------
        DataFrame
            - abs_BC_{wl}: BC absorption at each wavelength (Mm-1)
            - abs_BrC_{wl}: BrC absorption at each wavelength (Mm-1, NaN if invalid)
            - BrC_fraction_{wl}: BrC contribution fraction (0-1, NaN if invalid)
            - AAE_BrC: BrC Absorption Ångström Exponent (NaN if invalid)

        Examples
        --------
        >>> from AeroViz import RawDataReader, DataProcess
        >>> # Read AE33 data (has multi-wavelength absorption)
        >>> ae33 = RawDataReader(instrument='AE33', path='/data/AE33',
        ...                       start='2024-01-01', end='2024-01-31')
        >>> # Calculate BrC
        >>> optical = DataProcess(method='Optical')
        >>> brc_result = optical.BrC(ae33)
        >>> # Check valid data (non-NaN)
        >>> valid_brc = brc_result['AAE_BrC'].dropna()
        >>> print(valid_brc.mean())

        Notes
        -----
        The separation assumes AAE_BC ≈ 1.0 based on Mie theory for graphitic
        carbon. Real BC may have slightly different AAE depending on mixing
        state and size distribution.

        **Validity check**: If calculated BC absorption exceeds total absorption
        at ANY wavelength, the entire row is marked as invalid (NaN for all
        BrC-related values). This indicates the AAE=1 assumption is not valid.

        References
        ----------
        - Lack & Langridge (2013), ACP 13:8321-8341
        - Kirchstetter et al. (2004), JGR 109:D21208
        """
        from ._derived import calculate_BrC_absorption

        out = calculate_BrC_absorption(
            df_abs=df_abs,
            wavelengths=wavelengths,
            ref_wavelength=ref_wavelength,
            aae_bc=aae_bc
        )

        return self, out
