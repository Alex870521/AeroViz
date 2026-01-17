import numpy as np
from pandas import to_datetime, read_table, Series, DataFrame, concat

from AeroViz.rawDataReader.core import AbstractReader, QCRule, QCFlagBuilder


class Reader(AbstractReader):
    """APS (Aerodynamic Particle Sizer) Data Reader

    A specialized reader for APS data files, which measure particle size distributions
    in the range of 542-1981 nm (aerodynamic diameter).

    See full documentation at docs/source/instruments/APS.md for detailed information
    on supported formats and QC procedures.
    """
    nam = 'APS'

    # =========================================================================
    # QC Thresholds
    # =========================================================================
    MIN_HOURLY_COUNT = 5  # Minimum measurements per hour
    MIN_TOTAL_CONC = 1  # Minimum total concentration (#/cm³)
    MAX_TOTAL_CONC = 700  # Maximum total concentration (#/cm³)

    # Status Flags column name
    STATUS_COLUMN = 'Status Flags'
    # All zeros status means no error
    STATUS_OK = '0000 0000 0000 0000'

    # APS Status Flag bit definitions (from TSI RF command)
    # Format: bit_position: description
    ERROR_STATES = {
        0: 'Laser fault',
        1: 'Total Flow out of range',
        2: 'Sheath Flow out of range',
        3: 'Excessive sample concentration',
        4: 'Accumulator clipped',
        5: 'Autocal failed',
        6: 'Internal temperature < 10°C',
        7: 'Internal temperature > 40°C',
        8: 'Detector voltage out of range',
        # 9: Reserved (unused)
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._distributions = None  # Store distributions for separate file output

    def __call__(self, start, end, mean_freq='1h'):
        """
        Process APS data and save size distributions to separate files.

        Overrides AbstractReader.__call__ to add distribution file saving
        and filter out size bins from main output.

        Parameters
        ----------
        start : datetime
            Start time for data processing
        end : datetime
            End time for data processing
        mean_freq : str, default='1h'
            Frequency for resampling the data

        Returns
        -------
        pd.DataFrame
            Processed and resampled data (statistics only, no size bins)
        """
        # Call parent __call__ for standard processing
        result = super().__call__(start, end, mean_freq)

        # Save distributions to separate files
        self._save_distributions(mean_freq)

        # Filter out size bins from main output, keep only statistics
        stat_cols = [col for col in result.columns if not isinstance(col, (int, float))]
        result_stats = result[stat_cols]

        # Re-save filtered output to CSV
        result_stats.to_csv(self.csv_out)

        return result_stats

    def _raw_reader(self, file):
        """Read and parse raw APS data files.

        Handles files with multiple concatenated headers (when multiple APS export
        files are merged into one). Header rows are identified and filtered out.
        """
        import csv

        def find_header_row(file_obj, delimiter):
            csv_reader = csv.reader(file_obj, delimiter=delimiter)
            for skip, row in enumerate(csv_reader):
                if row and row[0] == 'Sample #':
                    return skip
            raise ValueError("Header row not found")

        def parse_date(df, date_format):
            if 'Date' in df.columns and 'Start Time' in df.columns:
                return to_datetime(df['Date'] + ' ' + df['Start Time'], format=date_format, errors='coerce')
            else:
                raise ValueError("Expected date columns not found")

        with open(file, 'r', encoding='utf-8', errors='ignore') as f:
            delimiter, date_formats = '\t', ['%m/%d/%y %H:%M:%S', '%m/%d/%Y %H:%M:%S']

            skip = find_header_row(f, delimiter)
            f.seek(0)

            _df = read_table(f, sep=delimiter, skiprows=skip, low_memory=False)

            # Handle transposed format
            if 'Date' not in _df.columns:
                try:
                    _df = _df.set_index('Sample #').T
                    _df.columns.name = None
                    _df = _df.reset_index(drop=True)
                except:
                    raise NotImplementedError('Not supported data format')

            # Parse date with multiple formats
            for date_format in date_formats:
                _time_index = parse_date(_df, date_format)
                if not _time_index.isna().all():
                    break
            else:
                raise ValueError("Unable to parse dates with given formats")

            # Set time index
            _df.index = _time_index
            _df.index.name = 'time'

            # Filter numeric columns (size bins ~542nm to ~1981nm)
            numeric_cols = []
            for col in _df.columns:
                col_str = str(col).strip()
                # Check if it's a numeric column (float-like)
                try:
                    val = float(col_str)
                    if 0.5 <= val <= 20:  # APS size range in μm
                        numeric_cols.append(col)
                except (ValueError, TypeError):
                    pass
            numeric_cols.sort(key=lambda x: float(str(x).strip()))

            _df_aps = _df[numeric_cols].copy()

            # Filter out invalid timestamps (NaT from embedded headers in merged files)
            _df_aps = _df_aps.loc[_df_aps.index.dropna().copy()]

            # Rename columns to float values
            _df_aps.columns = [round(float(str(col).strip()), 4) for col in _df_aps.columns]

            # Include Status Flags column in _df (will be processed by core together)
            if self.STATUS_COLUMN in _df.columns:
                _df_aps[self.STATUS_COLUMN] = _df.loc[_df_aps.index, self.STATUS_COLUMN].astype(str).str.strip()

            return _df_aps

    def _QC(self, _df):
        """
        Perform quality control on APS data.

        QC Rules Applied
        ----------------
        1. Status Error   : Non-zero status flags indicate instrument error
        2. Insufficient   : Less than 5 measurements per hour
        3. Invalid Number Conc : Total number concentration outside valid range (1-700 #/cm³)
        """
        _df = _df.copy()
        _index = _df.index.copy()

        # Filter to numeric columns only (exclude Status Flags)
        numeric_cols = [col for col in _df.columns if isinstance(col, (int, float))]
        df_numeric = _df[numeric_cols]

        # Calculate total concentration
        dlogDp = np.diff(np.log(df_numeric.columns.to_numpy(float))).mean()
        total_conc = df_numeric.sum(axis=1, min_count=1) * dlogDp

        # Calculate hourly data counts
        hourly_counts = (total_conc
                         .dropna()
                         .resample('h')
                         .size()
                         .resample('6min')
                         .ffill()
                         .reindex(df_numeric.index, method='ffill', tolerance='6min'))

        # Build QC rules declaratively
        qc = QCFlagBuilder()

        qc.add_rules([
            QCRule(
                name='Status Error',
                condition=lambda df: self.QC_control().filter_error_status(
                    _df, status_column=self.STATUS_COLUMN, status_type='binary_string'
                ),
                description='Non-zero status flags indicate instrument error'
            ),
            QCRule(
                name='Insufficient',
                condition=lambda df: Series(hourly_counts < self.MIN_HOURLY_COUNT, index=df.index).fillna(True),
                description=f'Less than {self.MIN_HOURLY_COUNT} measurements per hour'
            ),
            QCRule(
                name='Invalid Number Conc',
                condition=lambda df, tc=total_conc: Series(
                    (tc < self.MIN_TOTAL_CONC) | (tc > self.MAX_TOTAL_CONC),
                    index=df.index
                ).fillna(True),
                description=f'Total number concentration outside valid range ({self.MIN_TOTAL_CONC}-{self.MAX_TOTAL_CONC} #/cm³)'
            ),
        ])

        # Apply all QC rules
        df_qc = qc.apply(_df)

        # Store QC summary for combined output in _process()
        self._qc_summary = qc.get_summary(df_qc)

        return df_qc.reindex(_index)

    def _process(self, _df):
        """
        Calculate size distribution statistics from QC'd APS data.

        Processing Steps
        ----------------
        1. Calculate dlogDp from bin diameters
        2. Calculate number, surface, volume distributions (all in dX/dlogDp)
        3. Calculate total, GMD, GSD, mode for each weighting
        4. Calculate totals for size cutoffs: 1μm, 2.5μm, all
        5. Store distributions for separate file output

        Size Cutoffs (APS range: 0.542-19.81 μm)
        -----------------------------------------
        - 1μm: particles smaller than 1 μm
        - 2.5μm: particles smaller than 2.5 μm
        - all: full size range

        Parameters
        ----------
        _df : pd.DataFrame
            Quality-controlled DataFrame with size bin columns and QC_Flag

        Returns
        -------
        pd.DataFrame
            Original size bins (dN/dlogDp) + calculated statistics + QC_Flag
        """
        _index = _df.index.copy()

        # Separate QC_Flag from size bins
        qc_flag = _df['QC_Flag'].copy() if 'QC_Flag' in _df.columns else Series('Valid', index=_df.index)

        # Get numeric columns (size bins)
        bin_cols = [col for col in _df.columns if isinstance(col, (int, float))]
        df_bins = _df[bin_cols].copy()  # This is dN/dlogDp
        dp = np.array(bin_cols, dtype=float)  # in μm

        # Input is already dN/dlogDp, calculate dS/dlogDp and dV/dlogDp
        dN_dlogDp = df_bins.copy()
        dS_dlogDp = dN_dlogDp * np.pi * dp ** 2  # Surface area distribution (μm²·cm⁻³)
        dV_dlogDp = dN_dlogDp * np.pi * (dp ** 3) / 6  # Volume distribution (μm³·cm⁻³)

        # Store distributions for separate file output (with QC_Flag)
        self._distributions = {
            'dNdlogDp': concat([dN_dlogDp, qc_flag], axis=1),
            'dSdlogDp': concat([dS_dlogDp, qc_flag], axis=1),
            'dVdlogDp': concat([dV_dlogDp, qc_flag], axis=1),
        }

        # For statistics calculation, convert to absolute values (dX = dX/dlogDp * dlogDp)
        dlogDp = np.diff(np.log10(dp))
        dlogDp = np.append(dlogDp, dlogDp[-1])  # Extend to match length
        dN = dN_dlogDp * dlogDp  # Number concentration
        dS = dS_dlogDp * dlogDp  # Surface area
        dV = dV_dlogDp * dlogDp  # Volume

        # Calculate statistics
        stats = DataFrame(index=_df.index)

        # Size cutoffs in μm (APS bins are in μm)
        SIZE_CUTOFFS = {
            '1um': 1.0,  # 1 μm
            '2.5um': 2.5,  # 2.5 μm
            'all': np.inf  # All particles
        }

        # Calculate for each weighting type and size cutoff
        for weight_name, dist in [('num', dN), ('surf', dS), ('vol', dV)]:
            for cutoff_name, cutoff_um in SIZE_CUTOFFS.items():
                # Filter bins for this cutoff
                mask_bins = dp < cutoff_um
                if not mask_bins.any():
                    continue

                dp_cut = dp[mask_bins]
                dist_cut = dist.iloc[:, mask_bins]

                # Calculate total
                total = dist_cut.sum(axis=1, min_count=1)
                stats[f'total_{weight_name}_{cutoff_name}'] = total

                # Calculate GMD and GSD only for 'all' cutoff
                if cutoff_name == 'all':
                    total_valid = total.where(total > 0)

                    # GMD calculation (in log space)
                    log_dp = np.log(dp_cut)
                    gmd_log = (dist_cut * log_dp).sum(axis=1) / total_valid

                    # GSD calculation
                    dp_mesh, gmd_mesh = np.meshgrid(log_dp, gmd_log)
                    gsd_log = np.sqrt(((dp_mesh - gmd_mesh) ** 2 * dist_cut.values).sum(axis=1) / total_valid)

                    stats[f'GMD_{weight_name}'] = np.exp(gmd_log)
                    stats[f'GSD_{weight_name}'] = np.exp(gsd_log)

                    # Calculate mode (diameter with maximum concentration)
                    mask = dist_cut.notna().any(axis=1)
                    stats.loc[mask, f'mode_{weight_name}'] = dist_cut.loc[mask].idxmax(axis=1)

        # Combine: size bins + statistics + QC_Flag
        # (bins are kept for rate calculation, filtered out when saving to CSV)
        df_out = concat([df_bins, stats, qc_flag], axis=1)

        # Log QC summary
        if hasattr(self, '_qc_summary') and self._qc_summary is not None:
            self.logger.info(f"{self.nam} QC Summary:")
            for _, row in self._qc_summary.iterrows():
                self.logger.info(f"  {row['Rule']}: {row['Count']} ({row['Percentage']})")

        return df_out.reindex(_index)

    def _save_distributions(self, mean_freq: str = '1h') -> None:
        """
        Save size distributions to separate CSV files.

        Output Files
        ------------
        - output_aps_dNdlogDp.csv : Number distribution (dN/dlogDp)
        - output_aps_dSdlogDp.csv : Surface distribution (dS/dlogDp)
        - output_aps_dVdlogDp.csv : Volume distribution (dV/dlogDp)

        Parameters
        ----------
        mean_freq : str, default='1h'
            Frequency for resampling the data
        """
        if not hasattr(self, '_distributions') or self._distributions is None:
            self.logger.warning("No distributions to save. Run _process() first.")
            return

        output_folder = self.csv_out.parent
        self.logger.info("")

        for dist_name, dist_df in self._distributions.items():
            # Process QC_Flag: set invalid rows to NaN
            if 'QC_Flag' in dist_df.columns:
                invalid_mask = dist_df['QC_Flag'] != 'Valid'
                numeric_cols = [c for c in dist_df.columns if c != 'QC_Flag']
                dist_df.loc[invalid_mask, numeric_cols] = np.nan
                dist_df = dist_df.drop(columns=['QC_Flag'])

            # Resample and save
            dist_resampled = dist_df.resample(mean_freq).mean().round(4)
            output_path = output_folder / f'output_{self.nam.lower()}_{dist_name}.csv'
            dist_resampled.to_csv(output_path)
            self.logger.info(f"Saved: {output_path.name}")
