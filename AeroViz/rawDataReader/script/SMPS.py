import csv

import numpy as np
from pandas import to_datetime, to_numeric, read_csv, Series, concat, DataFrame

from AeroViz.rawDataReader.core import AbstractReader, QCRule, QCFlagBuilder


class Reader(AbstractReader):
    """SMPS (Scanning Mobility Particle Sizer) Data Reader

    A specialized reader for SMPS data files, which measure particle size distributions
    in the range of 11.8-593.5 nm.

    See full documentation at docs/source/instruments/SMPS.md for detailed information
    on supported formats and QC procedures.
    """
    nam = 'SMPS'

    # =========================================================================
    # QC Thresholds
    # =========================================================================
    MIN_HOURLY_COUNT = 5           # Minimum measurements per hour
    MIN_TOTAL_CONC = 2000          # Minimum total concentration (#/cm³)
    MAX_TOTAL_CONC = 1e7           # Maximum total concentration (#/cm³)
    MAX_LARGE_BIN_CONC = 4000      # Maximum concentration for >400nm bins (DMA water ingress indicator)
    LARGE_BIN_THRESHOLD = 400      # Size threshold for large bin filter (nm)

    # Status Flag column name
    STATUS_COLUMN = 'Status Flag'
    STATUS_OK = 'Normal Scan'  # Normal status text

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._status_data = None  # Store status flag data separately
        self._distributions = None  # Store distributions for separate file output

    def __call__(self, start, end, mean_freq='1h'):
        """
        Process SMPS data and save size distributions to separate files.

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
        """Read and parse raw SMPS data files."""

        def find_header_row(file_obj, delimiter):
            csv_reader = csv.reader(file_obj, delimiter=delimiter)
            for skip, row in enumerate(csv_reader):
                if row and (row[0] in ['Sample #', 'Scan Number']):
                    return skip
            raise ValueError("Header row not found")

        def parse_date(df, date_format):
            if 'Date' in df.columns and 'Start Time' in df.columns:
                return to_datetime(df['Date'] + ' ' + df['Start Time'], format=date_format, errors='coerce')
            elif 'DateTime Sample Start' in df.columns:
                return to_datetime(df['DateTime Sample Start'], format=date_format, errors='coerce')
            else:
                raise ValueError("Expected date columns not found")

        with open(file, 'r', encoding='utf-8', errors='ignore') as f:
            if file.suffix.lower() == '.txt':
                delimiter, date_formats = '\t', ['%m/%d/%y %X', '%m/%d/%Y %X']
            else:  # csv
                delimiter, date_formats = ',', ['%d/%m/%Y %X']

            skip = find_header_row(f, delimiter)
            f.seek(0)

            _df = read_csv(f, sep=delimiter, skiprows=skip, low_memory=False)
            if 'Date' not in _df.columns and 'DateTime Sample Start' not in _df.columns:
                try:
                    _df = _df.T
                    _df.columns = _df.iloc[0]
                    _df = _df.iloc[1:]
                    _df = _df.reset_index(drop=True)
                except:
                    raise NotImplementedError('Not supported date format')

            for date_format in date_formats:
                _time_index = parse_date(_df, date_format)
                if not _time_index.isna().all():
                    break
            else:
                raise ValueError("Unable to parse dates with given formats")

            # Check for comma decimal separator
            comma_decimal_cols = [col for col in _df.columns if ',' in col.strip()]
            if comma_decimal_cols:
                self.logger.warning(f"Detected {len(comma_decimal_cols)} columns using comma as decimal separator")
                _df.columns = _df.columns.str.replace(',', '.')

            # Filter numeric columns
            numeric_cols = [col for col in _df.columns if col.strip().replace('.', '').isdigit()]
            numeric_cols.sort(key=lambda x: float(x.strip()))

            _df.index = _time_index
            _df.index.name = 'time'

            _df_smps = _df[numeric_cols]
            _df_smps = _df_smps.loc[_df_smps.index.dropna().copy()]

            # Rename columns to float values (strip spaces)
            _df_smps.columns = [float(col.strip()) for col in _df_smps.columns]

            size_range = self.kwargs.get('size_range') or (11.8, 593.5)

            if _df_smps.columns[0] != size_range[0] or _df_smps.columns[-1] != size_range[1]:
                self.logger.warning(f'SMPS file: {file.name} size range mismatch. '
                                    f'Expected {size_range}, got ({_df_smps.columns[0]}, {_df_smps.columns[-1]})')
                return None

            _df_smps = _df_smps.apply(to_numeric, errors='coerce')

            # Extract Status Flag column if available (store separately, not in main df)
            if self.STATUS_COLUMN in _df.columns:
                # Get status values aligned with the filtered index
                status_col = _df.loc[_df_smps.index, self.STATUS_COLUMN].copy()
                # Clean status: strip whitespace
                status_col = status_col.astype(str).str.strip()
                # Accumulate status data
                if self._status_data is None:
                    self._status_data = status_col
                else:
                    self._status_data = concat([self._status_data, status_col])

            return _df_smps

    def _QC(self, _df):
        """
        Perform quality control on SMPS particle size distribution data.

        QC Rules Applied
        ----------------
        1. Status Error        : Non-empty status flag indicates instrument error
        2. Insufficient        : Less than 5 measurements per hour
        3. Invalid Number Conc : Total number concentration outside valid range (2000-1e7 #/cm³)
        4. DMA Water Ingress   : Bins >400nm with concentration > 4000 dN/dlogDp (indicates water in DMA)
        """
        _df = _df.copy()
        _index = _df.index.copy()

        # Get status flag from instance variable (populated during _raw_reader)
        status_flag = None
        if self._status_data is not None:
            # Align status data with current dataframe index
            status_flag = self._status_data.reindex(_df.index)

        # Apply size range filter
        size_range = self.kwargs.get('size_range') or (11.8, 593.5)
        numeric_cols = [col for col in _df.columns if isinstance(col, (int, float))]
        _df = _df[numeric_cols]
        size_mask = (_df.columns.astype(float) >= size_range[0]) & (_df.columns.astype(float) <= size_range[1])
        _df = _df.loc[:, size_mask]

        # Calculate total concentration for QC checks
        dlogDp = np.diff(np.log(_df.columns[:-1].to_numpy(float))).mean()
        total_conc = _df.sum(axis=1, min_count=1) * dlogDp

        # Calculate hourly data counts
        hourly_counts = (total_conc
                         .dropna()
                         .resample('h')
                         .size()
                         .resample('6min')
                         .ffill()
                         .reindex(_df.index, method='ffill', tolerance='6min'))

        # Get large bins (>400nm)
        large_bins = _df.columns[_df.columns.astype(float) >= self.LARGE_BIN_THRESHOLD]

        # Build QC rules declaratively
        qc = QCFlagBuilder()

        # Add Status Error rule if status flag is available
        if status_flag is not None:
            # Use default argument to capture status_flag value for proper type inference
            qc.add_rules([
                QCRule(
                    name='Status Error',
                    condition=lambda df, sf=status_flag: Series(
                        (sf != self.STATUS_OK) & (sf != '') & (sf != 'nan') & sf.notna(),
                        index=df.index
                    ).fillna(False),
                    description=f'Status flag is not "{self.STATUS_OK}"'
                ),
            ])

        qc.add_rules([
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
                description=f'Total number concentration outside valid range ({self.MIN_TOTAL_CONC}-{self.MAX_TOTAL_CONC:.0e} #/cm³)'
            ),
            QCRule(
                name='DMA Water Ingress',
                condition=lambda df: (df[large_bins] > self.MAX_LARGE_BIN_CONC).any(axis=1) if len(large_bins) > 0 else Series(False, index=df.index),
                description=f'Bins >{self.LARGE_BIN_THRESHOLD}nm with concentration > {self.MAX_LARGE_BIN_CONC} dN/dlogDp (water in DMA)'
            ),
        ])

        # Apply all QC rules
        df_qc = qc.apply(_df)

        # Store QC summary for combined output in _process()
        self._qc_summary = qc.get_summary(df_qc)

        return df_qc.reindex(_index)

    def _process(self, _df):
        """
        Calculate size distribution statistics from QC'd SMPS data.

        Processing Steps
        ----------------
        1. Calculate dlogDp from bin diameters
        2. Calculate number, surface, volume distributions (all in dX/dlogDp)
        3. Calculate total, GMD, GSD, mode for each weighting
        4. Calculate mode contributions (ultra, accum, coarse fractions)
        5. Store distributions for separate file output

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
        dp = np.array(bin_cols, dtype=float)

        # Input is already dN/dlogDp, calculate dS/dlogDp and dV/dlogDp
        dN_dlogDp = df_bins.copy()
        dS_dlogDp = dN_dlogDp * np.pi * dp ** 2  # Surface area distribution (nm²·cm⁻³)
        dV_dlogDp = dN_dlogDp * np.pi * (dp ** 3) / 6  # Volume distribution (nm³·cm⁻³)

        # Store distributions for separate file output (with QC_Flag)
        self._distributions = {
            'dNdlogDp': concat([dN_dlogDp, qc_flag], axis=1),
            'dSdlogDp': concat([dS_dlogDp, qc_flag], axis=1),
            'dVdlogDp': concat([dV_dlogDp, qc_flag], axis=1),
        }

        # For statistics calculation, convert to absolute values (dX = dX/dlogDp * dlogDp)
        dlogDp = np.diff(np.log10(dp))
        dlogDp = np.append(dlogDp, dlogDp[-1])
        dN = dN_dlogDp * dlogDp
        dS = dS_dlogDp * dlogDp
        dV = dV_dlogDp * dlogDp

        # Calculate statistics for all particles
        stats = DataFrame(index=_df.index)

        # Calculate for each weighting type
        for weight_name, dist in [('num', dN), ('surf', dS), ('vol', dV)]:
            total, gmd, gsd = self._geometric_prop(dp, dist)
            stats[f'total_{weight_name}'] = total
            stats[f'GMD_{weight_name}'] = gmd
            stats[f'GSD_{weight_name}'] = gsd

            # Calculate mode (diameter with maximum concentration)
            mask = dist.notna().any(axis=1)
            stats.loc[mask, f'mode_{weight_name}'] = dist.loc[mask].idxmax(axis=1)

            # Calculate mode contributions
            if weight_name == 'num':
                total_sum = dist.sum(axis=1)
                total_sum = total_sum.where(total_sum > 0)

                # Ultrafine: < 100 nm
                ultra_bins = [c for c in dist.columns if c < 100]
                if ultra_bins:
                    stats[f'ultra_{weight_name}'] = dist[ultra_bins].sum(axis=1) / total_sum

                # Accumulation: 100-1000 nm
                accum_bins = [c for c in dist.columns if 100 <= c < 1000]
                if accum_bins:
                    stats[f'accum_{weight_name}'] = dist[accum_bins].sum(axis=1) / total_sum

                # Coarse: >= 1000 nm (if available in SMPS range)
                coarse_bins = [c for c in dist.columns if c >= 1000]
                if coarse_bins:
                    stats[f'coarse_{weight_name}'] = dist[coarse_bins].sum(axis=1) / total_sum

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
        - output_smps_dNdlogDp.csv : Number distribution (dN/dlogDp)
        - output_smps_dSdlogDp.csv : Surface distribution (dS/dlogDp)
        - output_smps_dVdlogDp.csv : Volume distribution (dV/dlogDp)

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

    @staticmethod
    def _geometric_prop(dp, dist):
        """
        Calculate geometric mean diameter and geometric standard deviation.

        Parameters
        ----------
        dp : np.ndarray
            Particle diameters (nm)
        dist : pd.DataFrame
            Distribution data (dN, dS, or dV)

        Returns
        -------
        tuple
            (total, GMD, GSD) as pandas Series
        """
        # Total concentration
        total = dist.sum(axis=1, min_count=1)
        total_valid = total.where(total > 0)

        # GMD calculation (in log space)
        log_dp = np.log(dp)
        gmd_log = (dist * log_dp).sum(axis=1) / total_valid

        # GSD calculation
        dp_mesh, gmd_mesh = np.meshgrid(log_dp, gmd_log)
        gsd_log = np.sqrt(((dp_mesh - gmd_mesh) ** 2 * dist.values).sum(axis=1) / total_valid)

        return total, np.exp(gmd_log), np.exp(gsd_log)
