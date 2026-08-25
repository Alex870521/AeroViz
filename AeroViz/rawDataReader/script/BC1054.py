from pandas import read_csv, to_numeric, to_datetime, concat

from AeroViz.rawDataReader.core import AbstractReader, QCRule, QCFlagBuilder, WARNING
from AeroViz.rawDataReader.core.pre_process import _absCoe


class Reader(AbstractReader):
    """BC1054 Black Carbon Monitor Data Reader

    A specialized reader for BC1054 data files, which measure black carbon
    concentrations using light absorption at 10 wavelengths.

    See ``docs/api/instruments/aethalometers/BC1054.md`` for usage and
    ``docs/guide/instrument-qc.md`` for the
    file layout, status codes and QC rules.
    """
    nam = 'BC1054'

    # =========================================================================
    # Column Definitions
    # =========================================================================
    BC_COLUMNS = ['BC1', 'BC2', 'BC3', 'BC4', 'BC5', 'BC6', 'BC7', 'BC8', 'BC9', 'BC10']
    ABS_COLUMNS = ['abs_370', 'abs_430', 'abs_470', 'abs_525', 'abs_565',
                   'abs_590', 'abs_660', 'abs_700', 'abs_880', 'abs_950']
    CAL_COLUMNS = ['abs_550', 'AAE', 'eBC']

    #: `Invalid AAE` needs the derived AAE column, so it is raised in
    #: `_process` via `update_qc_flag`, not as a `QCRule`.
    LATE_QC_FLAGS = ('Invalid AAE',)

    # =========================================================================
    # QC Thresholds
    # =========================================================================
    MIN_BC = 0           # Minimum BC concentration (ng/m³)
    MAX_BC = 20000       # Maximum BC concentration (ng/m³)
    MIN_AAE = 0.7        # Minimum valid AAE
    MAX_AAE = 3.0        # Maximum valid AAE — loose enough to keep BrC-rich
                         # biomass burning / dust episodes, where bulk AAE runs 2-3

    #: Where the instrument's own timestamp is kept when a file carries both
    #: clocks. The index uses the logger clock; see `_check_clock_offset`.
    INSTRUMENT_TIME_COLUMN = 'Instrument_Time'
    #: Ignore disagreements at or below this — the manual labels records at the
    #: end of the minute, so a minute of slack is expected bookkeeping.
    CLOCK_TOLERANCE_S = 60

    # =========================================================================
    # Status Error Codes (bitwise flags)
    # =========================================================================
    ERROR_STATES = [
        1,      # Power Failure
        2,      # Digital Sensor Link Failure
        4,      # Tape Move Failure
        8,      # Maintenance
        16,     # Flow Failure
        32,     # Automatic Tape Advance
        64,     # Detector Failure
        256,    # Sensor Range
        512,    # Nozzle Move Failure
        1024,   # SPI Link Failure
        2048,   # Calibration Audit
        65536,  # Tape Move
    ]

    #: Named conditions in the status register, `{decimal: name}` — the same
    #: contract every reader with a documented register uses, so one decoder
    #: serves them all (`_status_condition_rows`). Mirrors `ERROR_STATES`
    #: above; that list decides what counts as an error, this map decides what
    #: it is called.
    STATUS_BITS = {
        1: 'Power Failure',
        2: 'Digital Sensor Link Failure',
        4: 'Tape Move Failure',
        8: 'Maintenance',
        16: 'Flow Failure',
        32: 'Automatic Tape Advance',
        64: 'Detector Failure',
        256: 'Sensor Range',
        512: 'Nozzle Move Failure',
        1024: 'SPI Link Failure',
        2048: 'Calibration Audit',
        65536: 'Tape Move',
    }

    def _raw_reader(self, file):
        """Read and parse raw BC1054 data files.

        Returns all columns from the raw file. Column selection is deferred
        to _QC() and _process() stages.
        """
        with open(file, 'r', encoding='utf-8', errors='ignore') as f:
            # Locate the column header row by looking for a line whose first
            # token is "Time" or "Raw_Time". Header variants seen in the wild:
            #   - Column header on line 1 directly         (NZ 2024)
            #   - "Raw_Time,Time,..." on line 1            (NZ 2025)
            #   - "Data Report"/"User Report" + 3 metadata lines + header (TP)
            #   - Leading blank line(s) before all of the above (TP 2024)
            skip = 0
            for i in range(20):
                pos = f.tell()
                line = f.readline()
                if not line:
                    break
                first_token = line.lstrip().split(',', 1)[0].strip().lower()
                if first_token in ("time", "raw_time"):
                    skip = i
                    break
            f.seek(0)
            _df = read_csv(f, parse_dates=True, index_col=0, skiprows=skip)
            _df.columns = _df.columns.str.replace(' ', '')

            _df = _df.rename(columns={
                'BC1(ng/m3)': 'BC1', 'BC2(ng/m3)': 'BC2', 'BC3(ng/m3)': 'BC3',
                'BC4(ng/m3)': 'BC4', 'BC5(ng/m3)': 'BC5', 'BC6(ng/m3)': 'BC6',
                'BC7(ng/m3)': 'BC7', 'BC8(ng/m3)': 'BC8', 'BC9(ng/m3)': 'BC9',
                'BC10(ng/m3)': 'BC10',
                'Flow(lpm)': 'Flow', 'DFlow(lpm)': 'DFlow',
                'WS(m/s)': 'WS', 'WD(Deg)': 'WD',
                'AT(C)': 'AT', 'RH(%)': 'RH', 'BP(mbar)': 'BP',
            })

            # Keep the instrument's own clock alongside the logger's, and say so
            # when they disagree — see `_check_clock_offset`.
            if 'Time' in _df.columns:
                _df = _df.rename(columns={'Time': self.INSTRUMENT_TIME_COLUMN})
                self._check_clock_offset(_df, file)

            return _df.loc[~_df.index.duplicated() & _df.index.notna()]

    def _check_clock_offset(self, _df, file) -> None:
        """Report a disagreement between the logger clock and the instrument's.

        A file with both columns has two different clocks in it:

        ``Raw_Time``
            not a Met One field — it does not appear anywhere in the BC 1054
            manual — so it comes from whatever logged or downloaded the file, and
            runs on that host's clock.
        ``Time``
            the manual's own definition: *"the date and timestamp for the data
            record. The timestamp is end of the minute."* That comes from the
            instrument's internal RTC, which an operator sets by hand (manual
            §3.5.7, "The CLOCK Setup Screen") and which can therefore be wrong.

        Both are kept. The index stays on ``Raw_Time`` because the measurement
        happened at the wall-clock instant regardless of what the instrument
        believed the time was, and because in the corpus it is the well-behaved
        one: strictly increasing, no duplicates. The instrument clock is not —
        one fixture repeats timestamps and jumps 14 h 42 m mid-file, and another
        sits a constant **12 h 04 m** behind for all 1440 rows of a day, the
        signature of an RTC set 12 hours out (AM/PM) plus drift.

        That offset used to vanish silently: the column was dropped right here.
        Losing it also loses the only evidence that an instrument's clock needs
        resetting, so it is now recorded and reported.
        """
        instrument = to_datetime(_df[self.INSTRUMENT_TIME_COLUMN], errors='coerce')
        offset = (_df.index.to_series() - instrument).dt.total_seconds().dropna()
        if offset.empty:
            return

        median = offset.median()
        if abs(median) <= self.CLOCK_TOLERANCE_S:
            return

        self.logger.warning(
            f"{file.name}: the instrument clock is {self._format_offset(median)} "
            f"{'behind' if median > 0 else 'ahead of'} the logger clock "
            f"(median over {len(offset)} rows; "
            f"range {self._format_offset(offset.min())} to {self._format_offset(offset.max())}). "
            f"The index uses the logger clock (`Raw_Time`); the instrument's own "
            f"timestamp is kept as `{self.INSTRUMENT_TIME_COLUMN}`. An offset near "
            f"12 h usually means the instrument's clock is set to the wrong "
            f"AM/PM — worth fixing at the instrument (manual 3.5.7, SET CLOCK).")

    @staticmethod
    def _format_offset(seconds: float) -> str:
        """Seconds as ``12h04m`` / ``60s``, whichever reads better."""
        seconds = abs(float(seconds))
        if seconds < 60:
            return f'{seconds:.0f}s'
        if seconds < 3600:
            return f'{seconds / 60:.0f}m'
        return f'{int(seconds // 3600)}h{int((seconds % 3600) // 60):02d}m'

    def _QC(self, _df):
        """
        Perform quality control on BC1054 raw data.

        QC Rules Applied (raw data only)
        ---------------------------------
        1. Duplicate      : Consecutive duplicate rows removed
        2. Status Error   : Invalid instrument status codes
        3. Invalid BC     : BC concentration outside 0-20000 ng/m³
        4. Insufficient   : Less than 50% hourly data completeness

        Note: AAE validation is done in _process() after calculation.
        """
        _index = _df.index.copy()

        # Remove consecutive duplicate rows
        duplicate_rows = _df.eq(_df.shift()).all(axis=1) | _df.eq(_df.shift(-1)).all(axis=1)
        df_qc = _df[~duplicate_rows].copy()

        # Warn if the status column is missing: `filter_error_status` would
        # otherwise report "no errors" for a renamed column.
        self.check_status_columns(df_qc, ['Status'])

        # Build QC rules declaratively
        qc = self.qc_builder()
        qc.add_rules([
            QCRule(
                name='Status Error',
                condition=lambda df: self.QC_control().filter_error_status(
                    df, self.ERROR_STATES,
                    ignored_values=self.kwargs.get('ignored_status_errors')),
                description='Invalid instrument status code detected'
            ),
            QCRule(
                name='Invalid BC',
                condition=lambda df: ((df[self.BC_COLUMNS] <= self.MIN_BC) |
                                      (df[self.BC_COLUMNS] > self.MAX_BC)).any(axis=1),
                description=f'BC concentration outside valid range {self.MIN_BC}-{self.MAX_BC} ng/m³'
            ),
            QCRule(
                name='Insufficient',
                condition=lambda df: self.QC_control().hourly_completeness_QC(
                    df[self.BC_COLUMNS], freq=self._resolved_freq or self.meta['freq']
                ),
                description='Less than 50% hourly data completeness',
                # Representativeness, not validity: the readings in a sparse
                # hour are fine, it is an average over that hour that would
                # misrepresent it. Users were losing the head and tail of
                # every read to this. Promote it per run with
                # flag_severity={'Insufficient': 'error'}.
                severity=WARNING,
            ),
        ])

        # Apply all QC rules and get flagged DataFrame
        df_qc = qc.apply(df_qc)

        # Store QC summary for combined output in _process()
        self._qc_summary = qc.get_summary(df_qc)

        return df_qc.reindex(_index)

    def _process(self, _df):
        """
        Calculate absorption coefficients and validate derived parameters.

        Processing Steps
        ----------------
        1. Calculate absorption coefficients at each wavelength
        2. Calculate AAE (Absorption Ångström Exponent)
        3. Calculate eBC (equivalent Black Carbon)
        4. Validate AAE range and update QC_Flag
        """
        _index = _df.index.copy()

        # Calculate absorption coefficients, AAE, and eBC
        _df_cal = _absCoe(_df[self.BC_COLUMNS], instru=self.nam, specified_band=[550])

        # Preserve all original columns (metadata like Flow, AT, RH, BP, etc.)
        non_bc_cols = [c for c in _df.columns if c not in self.BC_COLUMNS]
        df_out = concat([_df_cal, _df[non_bc_cols]], axis=1)

        # Validate AAE and update QC_Flag
        invalid_aae = (df_out['AAE'] < self.MIN_AAE) | (df_out['AAE'] > self.MAX_AAE)
        df_out = self.update_qc_flag(df_out, invalid_aae, 'Invalid AAE')

        # Log the combined summary: `Invalid AAE` can only be counted here,
        # once _absCoe has produced the AAE column.
        if self._qc_summary is not None:
            self.log_qc_summary(self.extend_qc_summary(
                self._qc_summary, df_out, 'Invalid AAE', invalid_aae,
                description=f'AAE outside valid range {self.MIN_AAE}-{self.MAX_AAE}'))

        return df_out.reindex(_index)
