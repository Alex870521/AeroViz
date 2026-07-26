from pandas import read_csv, to_datetime, to_numeric, Series

from AeroViz.rawDataReader.core import AbstractReader, QCRule, QCFlagBuilder, WARNING


class Reader(AbstractReader):
    """Xact 625i XRF Analyzer Data Reader

    A specialized reader for Xact 625i continuous XRF analyzer data files,
    which measure elemental composition of particulate matter.
    """
    nam = 'Xact'

    #: Sample time (minutes) observed in the parsed files; selects which column of
    #: `MANUAL_MDL` applies. None until a file has been read.
    _sample_time = None

    # Element symbols with atomic numbers (extracted from column headers)
    ELEMENTS = [
        'Mg', 'Al', 'Si', 'P', 'S', 'Cl', 'Ar', 'K', 'Ca', 'Sc', 'Ti', 'V', 'Cr', 'Mn', 'Fe',
        'Co', 'Ni', 'Cu', 'Zn', 'Ga', 'Ge', 'As', 'Se', 'Br', 'Rb', 'Sr', 'Y', 'Zr', 'Nb', 'Mo',
        'Ru', 'Rh', 'Pd', 'Ag', 'Cd', 'In', 'Sn', 'Sb', 'Te', 'I', 'Cs', 'Ba', 'La', 'Ce',
        'Pr', 'Nd', 'Pm', 'Sm', 'Eu', 'Gd', 'Tb', 'Dy', 'Ho', 'Er', 'Tm', 'Yb', 'Lu',
        'Hf', 'Ta', 'W', 'Re', 'Os', 'Ir', 'Pt', 'Au', 'Hg', 'Tl', 'Pb', 'Bi', 'Th', 'Pa', 'U'
    ]

    # Environmental/status columns to keep
    ENV_COLUMNS = [
        'AT', 'SAMPLE_T', 'BP', 'TAPE', 'FLOW_25', 'FLOW_ACT', 'FLOW_STD', 'VOLUME',
        'TUBE_T', 'ENCLOSURE_T', 'FILAMENT_V', 'SDD_T', 'DPP_T', 'RH',
        'WIND', 'WIND_DIR', 'SAMPLE_TIME', 'ALARM', 'SAMPLE_TYPE'
    ]

    # =========================================================================
    # Alarm Code Definitions
    # =========================================================================
    # Error codes (100-110) - indicate instrument malfunction, invalidate data
    ERROR_CODES = {
        100: 'Xray Voltage Error',
        101: 'Xray Current Error',
        102: 'Tube Temperature Error',
        103: 'Enclosure Temperature Error',
        104: 'Tape Error',
        105: 'Pump Error',
        106: 'Filter Wheel Error',
        107: 'Dynamic Rod Error',
        108: 'Nozzle Error',
        109: 'Energy Calibration Error',
        110: 'Software Error',
    }

    # Warning codes (200-203) - indicate upscale warnings
    WARNING_CODES = {
        200: 'Upscale Cr Warning',
        201: 'Upscale Pb Warning',
        202: 'Upscale Cd Warning',
        203: 'Upscale Nb Warning',
    }

    # =========================================================================
    # Detection limits - Xact 625i Operation Manual, Appendix "Xact 625i Minimum
    # Detection Limits" (p.73)
    # =========================================================================
    # ng/m3, keyed by element then by sample time in minutes. Straight from the
    # manual; the file's own SAMPLE_TIME column selects which column to use.
    #
    # The manual's footnote matters for how these are used: they are
    # "interference free ONE SIGMA detection limits for 0.707 inch2 spot sample
    # size at 68% Confidence Level (C1sigma) per US EPA IO 3.3 and Currie, 1968."
    #
    # One sigma, not three. The `{element}_uncert` column the instrument writes is
    # the same 1-sigma quantity, which is what makes Currie's criteria directly
    # applicable to it:
    #     value >= 3 * uncert   -> detected      (~99% confidence)
    #     value >= 10 * uncert  -> quantifiable
    # See `element_reliability`.
    #
    # The manual specifies 29 elements. The instrument reports more (72 in the
    # corpus) because each unit is "precisely calibrated for the user requested
    # elements of interest" (manual 5.6) - but for anything outside this table CES
    # publishes no detection limit, so a number in that column has no stated
    # accuracy. `element_reliability` marks those separately rather than treating
    # them as measurements.
    MANUAL_MDL = {
        'Al': {15: 840, 30: 290, 60: 100, 120: 35, 180: 19, 240: 12},
        'Si': {15: 150, 30: 51, 60: 17.8, 120: 6.3, 180: 3.4, 240: 2.2},
        'P': {15: 44, 30: 15, 60: 5.2, 120: 1.8, 180: 0.99, 240: 0.64},
        'S': {15: 26, 30: 9.1, 60: 3.16, 120: 1.1, 180: 0.6, 240: 0.39},
        'Cl': {15: 15, 30: 5, 60: 1.73, 120: 0.61, 180: 0.33, 240: 0.21},
        'K': {15: 9.8, 30: 3.4, 60: 1.17, 120: 0.41, 180: 0.22, 240: 0.14},
        'Ca': {15: 2.5, 30: 0.86, 60: 0.3, 120: 0.1, 180: 0.057, 240: 0.037},
        'Ti': {15: 1.3, 30: 0.46, 60: 0.16, 120: 0.056, 180: 0.03, 240: 0.02},
        'V': {15: 1, 30: 0.34, 60: 0.12, 120: 0.042, 180: 0.023, 240: 0.015},
        'Cr': {15: 0.97, 30: 0.33, 60: 0.12, 120: 0.041, 180: 0.022, 240: 0.014},
        'Mn': {15: 1.2, 30: 0.41, 60: 0.14, 120: 0.05, 180: 0.027, 240: 0.018},
        'Fe': {15: 1.4, 30: 0.49, 60: 0.17, 120: 0.061, 180: 0.033, 240: 0.021},
        'Co': {15: 1.1, 30: 0.39, 60: 0.14, 120: 0.049, 180: 0.026, 240: 0.017},
        'Ni': {15: 0.78, 30: 0.27, 60: 0.1, 120: 0.034, 180: 0.018, 240: 0.012},
        'Cu': {15: 0.65, 30: 0.23, 60: 0.079, 120: 0.028, 180: 0.015, 240: 0.01},
        'Zn': {15: 0.55, 30: 0.19, 60: 0.067, 120: 0.023, 180: 0.013, 240: 0.008},
        'As': {15: 0.52, 30: 0.18, 60: 0.063, 120: 0.022, 180: 0.012, 240: 0.008},
        'Se': {15: 0.66, 30: 0.23, 60: 0.081, 120: 0.029, 180: 0.016, 240: 0.01},
        'Br': {15: 0.85, 30: 0.3, 60: 0.1, 120: 0.037, 180: 0.02, 240: 0.013},
        'Ag': {15: 16, 30: 5.5, 60: 1.9, 120: 0.68, 180: 0.37, 240: 0.24},
        'Cd': {15: 21, 30: 7.2, 60: 2.5, 120: 0.89, 180: 0.48, 240: 0.31},
        'In': {15: 26, 30: 8.9, 60: 3.1, 120: 1.1, 180: 0.6, 240: 0.39},
        'Sn': {15: 33, 30: 12, 60: 4.1, 120: 1.4, 180: 0.78, 240: 0.51},
        'Sb': {15: 42, 30: 15, 60: 5.2, 120: 1.8, 180: 0.99, 240: 0.64},
        'Ba': {15: 3.3, 30: 1.1, 60: 0.39, 120: 0.14, 180: 0.074, 240: 0.048},
        'Hg': {15: 0.99, 30: 0.35, 60: 0.12, 120: 0.043, 180: 0.023, 240: 0.015},
        'Tl': {15: 0.95, 30: 0.33, 60: 0.12, 120: 0.041, 180: 0.022, 240: 0.014},
        'Pb': {15: 1, 30: 0.36, 60: 0.13, 120: 0.045, 180: 0.024, 240: 0.016},
        'Bi': {15: 1.1, 30: 0.37, 60: 0.13, 120: 0.046, 180: 0.025, 240: 0.016},
    }

    #: Sample times the manual tabulates, in minutes.
    MANUAL_SAMPLE_TIMES = (15, 30, 60, 120, 180, 240)

    # Currie criteria applied to the reported 1-sigma uncertainty.
    DETECTION_SIGMA = 3        # value >= 3 sigma  -> detected
    QUANTIFICATION_SIGMA = 10  # value >= 10 sigma -> quantifiable
    #: Fraction of a run's samples that must reach a criterion for the element to
    #: be classed as such. Deliberately high: an element that is only sometimes
    #: quantifiable is not one you can build a time series from.
    RELIABLE_FRACTION = 0.75

    # =========================================================================
    # QC Thresholds
    # =========================================================================
    MIN_VALUE = 0
    MAX_VALUE = 100000  # ng/m3

    # Internal standard (Nb) QC parameters
    INTERNAL_STD_ELEMENT = 'Nb'
    INTERNAL_STD_TOLERANCE = 0.20  # ±20% from median

    @property
    def MDL(self) -> dict:
        """Per-element 1σ detection limits (ng/m³) for this run's sample time.

        The manual's table wins where it has an entry, because it is the vendor's
        own specification *and* it varies with sample time — a 15-minute sample
        has ~8× the detection limit of a 60-minute one, so a single fixed number
        is only right for one configuration. `config/supported_instruments.py`
        supplies the rest (elements CES publishes no limit for); those are marked
        as unverified by `element_reliability`.

        Used for the per-element below-MDL diagnostic, never as a row-level flag
        — see `log_below_mdl`.
        """
        limits = {k: v for k, v in (self.meta.get('MDL') or {}).items() if v is not None}
        limits.update(self.manual_mdl())
        return limits

    def manual_mdl(self, sample_time: float | None = None) -> dict:
        """The manual's detection limits at ``sample_time`` minutes.

        Falls back to the sample time seen in the data (`SAMPLE_TIME`), then to
        60 minutes. A time between two tabulated ones takes the *longer* column,
        which is the conservative direction: a shorter sample cannot have a lower
        detection limit than the manual quotes for a longer one.
        """
        if sample_time is None:
            sample_time = self._sample_time or 60

        candidates = [t for t in self.MANUAL_SAMPLE_TIMES if t <= sample_time]
        column = max(candidates) if candidates else min(self.MANUAL_SAMPLE_TIMES)
        return {element: limits[column] for element, limits in self.MANUAL_MDL.items()}

    def element_reliability(self, df) -> 'pd.DataFrame':
        """Classify each element by how well the instrument actually measured it.

        The `{element}_uncert` columns are 1σ uncertainties on the same basis as
        the manual's detection limits, so Currie's criteria apply directly:
        a value is *detected* at ``>= 3σ`` and *quantifiable* at ``>= 10σ``. An
        element is classed by the fraction of the run's samples reaching each:

        ``quantitative``       usable as a time series
        ``semi-quantitative``  detected, but the magnitudes carry large error
        ``below-detection``    reported, but indistinguishable from noise

        Whether the *manual* specifies the element is reported separately, in
        ``manual_mdl`` / ``published_limit``. The two axes are independent and
        both matter: an element measured at 100 sigma with no published detection
        limit (the internal standard, Nb) is empirically solid but has no vendor
        accuracy to appeal to, while one that is in the manual and still sits
        below detection is simply not present at this site. Collapsing them would
        hide one or the other.

        This is per **element**, not per row, and that is the point: on a 45-column
        XRF frame the interesting question is never "is this row bad" but "which
        of these columns can I use". A row-level rule over all elements fires on
        ~100 % of rows (measured), which says nothing.

        Returns a DataFrame indexed by element, worst first.
        """
        import pandas as pd

        manual = self.manual_mdl()
        rows = []
        for element in [c for c in df.columns if c in self.ELEMENTS]:
            uncert_column = f'{element}_uncert'
            if uncert_column not in df.columns:
                continue

            value = pd.to_numeric(df[element], errors='coerce')
            sigma = pd.to_numeric(df[uncert_column], errors='coerce')
            usable = value.notna() & sigma.notna() & (sigma > 0)
            n = int(usable.sum())

            if not n:
                detected = quantifiable = 0.0
                relative = float('nan')
            else:
                v, s = value[usable], sigma[usable]
                detected = float((v >= self.DETECTION_SIGMA * s).mean())
                quantifiable = float((v >= self.QUANTIFICATION_SIGMA * s).mean())
                relative = float((s / v.where(v != 0)).median())

            if quantifiable >= self.RELIABLE_FRACTION:
                verdict = 'quantitative'
            elif detected >= self.RELIABLE_FRACTION:
                verdict = 'semi-quantitative'
            else:
                verdict = 'below-detection'

            rows.append({
                'element': element,
                'verdict': verdict,
                'published_limit': element in manual,
                'n': n,
                'detected': round(detected * 100, 1),
                'quantifiable': round(quantifiable * 100, 1),
                'median_rel_uncert': round(relative * 100, 1) if relative == relative else None,
                'manual_mdl': manual.get(element),
            })

        if not rows:
            return pd.DataFrame(columns=['element', 'verdict', 'published_limit', 'n',
                                         'detected', 'quantifiable', 'median_rel_uncert',
                                         'manual_mdl'])

        order = {'below-detection': 0, 'semi-quantitative': 1, 'quantitative': 2}
        return (pd.DataFrame(rows)
                .sort_values(['verdict', 'quantifiable'], key=lambda c: c.map(order).fillna(c))
                .set_index('element'))

    def _raw_reader(self, file):
        """Read and parse raw Xact 625i XRF data files.

        Returns all columns from the raw file. Column selection is deferred
        to _QC() and _process() stages.
        """
        with open(file, 'r', encoding='utf-8', errors='ignore') as f:
            f.readline()  # skip row 0 (element names)
            headers = f.readline().strip().split(',')
            headers.append('_extra_')  # data has one extra field at end
            _df = read_csv(f, names=headers, on_bad_lines='skip')

        # Parse time column
        _df['time'] = to_datetime(_df['TIME'], format='%m/%d/%Y %H:%M:%S', errors='coerce')
        _df = _df.set_index('time')
        _df = _df.loc[~_df.index.duplicated() & _df.index.notna()]

        # Filter out calibration samples BEFORE rounding to avoid losing valid 00:30 samples
        # Xact does daily QA checks at midnight (00:00-00:30), SAMPLE_TYPE: 1=normal, 2=calibration
        if 'Sample Type' in _df.columns:
            _df = _df[_df['Sample Type'] == 1]

        _df.index = _df.index.round('1h')

        # Rename environmental/status columns
        rename_map = {
            'AT (C)': 'AT',
            'SAMPLE (C)': 'SAMPLE_T',
            'BP (mmHg)': 'BP',
            'TAPE (mmHg)': 'TAPE',
            'FLOW 25 (slpm)': 'FLOW_25',
            'FLOW ACT (lpm)': 'FLOW_ACT',
            'FLOW STD (slpm)': 'FLOW_STD',
            'VOLUME (L)': 'VOLUME',
            'TUBE (C)': 'TUBE_T',
            'ENCLOSURE (C)': 'ENCLOSURE_T',
            'FILAMENT (V)': 'FILAMENT_V',
            'SDD (C)': 'SDD_T',
            'DPP (C)': 'DPP_T',
            'RH (%)': 'RH',
            'WIND (m/s)': 'WIND',
            'WIND DIR (deg)': 'WIND_DIR',
            'SAMPLE TIME (min)': 'SAMPLE_TIME',
            'ALARM': 'ALARM',
            'Sample Type': 'SAMPLE_TYPE'
        }

        # Build element column rename map
        for col in _df.columns:
            for elem in self.ELEMENTS:
                # Match pattern like "Mg 12 (ng/m3)" or " K 19 (ng/m3)" for concentration
                if f'{elem} ' in col and '(ng/m3)' in col and 'uncert' not in col.lower():
                    rename_map[col] = elem
                # Match pattern like "Al Uncert (ng/m3)" or "Mg uncert (ng/m3)" for uncertainty
                elif f'{elem} ' in col and 'uncert' in col.lower():
                    rename_map[col] = f'{elem}_uncert'

        _df = _df.rename(columns=rename_map)

        # Drop parsing artifacts, consumed index columns, and non-data string columns
        _df = _df.drop(columns=['_extra_', 'TIME', 'PUMP START TIME', 'Output Pin 7 (True=ON)', 'XC VER'],
                        errors='ignore')

        # Detection limits depend on how long each sample was collected, so keep
        # what the file says (the manual tabulates 15/30/60/120/180/240 min).
        if 'SAMPLE_TIME' in _df.columns:
            observed = to_numeric(_df['SAMPLE_TIME'], errors='coerce').dropna()
            if not observed.empty:
                self._sample_time = float(observed.mode().iloc[0])

        return _df.loc[~_df.index.duplicated() & _df.index.notna()]

    def _QC(self, _df):
        """Perform quality control on Xact XRF data.

        QC Rules Applied
        ----------------
        1. Calibration Mode      : SAMPLE_TYPE != 1 indicates zero calibration
        2. Instrument Error      : ALARM code 100-110 indicates instrument error
        3. Upscale Warning       : ALARM code 200-203 indicates upscale warning
        4. Invalid Value         : Element concentration outside valid range (0-100000 ng/m3)
        5. Internal Std Drift    : Nb internal standard deviates ±20% from median

        Detection limits (`MDL`, from the config) are reported per element in the
        log rather than flagged: with 45 elements, "any element below its MDL" is
        true for practically every row, and a non-`Valid` flag NaNs the whole row
        downstream — flagging it would delete the dataset. See `log_below_mdl`.
        """
        _index = _df.index.copy()
        df_qc = _df.copy()

        # Get element columns (exclude uncertainty and environmental columns)
        element_cols = [col for col in df_qc.columns if col in self.ELEMENTS]
        uncert_cols = [f'{elem}_uncert' for elem in element_cols if f'{elem}_uncert' in df_qc.columns]

        # Build QC rules declaratively
        qc = self.qc_builder()

        # Add Calibration Mode rule (SAMPLE_TYPE: 1=normal sampling, 2=zero calibration)
        # Note: Most calibration samples are already filtered in _raw_reader, this catches any remaining
        if 'SAMPLE_TYPE' in df_qc.columns:
            qc.add_rules([
                QCRule(
                    name='Calibration Mode',
                    condition=lambda df: (df['SAMPLE_TYPE'] != 1) & df['SAMPLE_TYPE'].notna(),
                    description='Instrument in calibration mode (SAMPLE_TYPE != 1)'
                ),
            ])

        # Add Instrument Error rule (ALARM codes 100-110)
        if 'ALARM' in df_qc.columns:
            qc.add_rules([
                QCRule(
                    name='Instrument Error',
                    condition=lambda df: df['ALARM'].isin(list(self.ERROR_CODES.keys())),
                    description='Instrument error detected (ALARM code 100-110)'
                ),
                QCRule(
                    name='Upscale Warning',
                    condition=lambda df: df['ALARM'].isin(list(self.WARNING_CODES.keys())),
                    description='Upscale warning detected (ALARM code 200-203)',
                    # The instrument distinguishes errors (100-110) from warnings
                    # (200-203); honour that. An upscale warning means a channel is
                    # near the top of its calibration, not that the row is broken.
                    severity=WARNING,
                ),
            ])

        # Add Invalid Value rule
        if element_cols:
            qc.add_rules([
                QCRule(
                    name='Invalid Value',
                    condition=lambda df, cols=element_cols: (
                            (df[cols] < self.MIN_VALUE) | (df[cols] > self.MAX_VALUE)
                    ).any(axis=1),
                    description=f'Concentration outside valid range ({self.MIN_VALUE}-{self.MAX_VALUE} ng/m3)'
                ),
            ])

        # Add High Uncertainty rule, scoped to the elements this run measures well.
        #
        # The instrument reports a value and a 1-sigma uncertainty for every
        # element. Flagging a row whenever *any* element fails Currie's 3-sigma
        # test fires on ~100% of rows (measured on both fixtures) because a dozen
        # elements are permanently below detection at any real site — that is a
        # property of the element, not of the row, and `element_reliability`
        # reports it per element instead.
        #
        # What IS a row-level event: an element that this run otherwise measures
        # well going noisy. So the rule watches only the `quantitative` elements,
        # and fires when one of them reports a value above its detection limit
        # while its own uncertainty says the value is not distinguishable from
        # noise. On the fixtures: 0% of clean rows, 8% of the degraded ones, and
        # there it caught S, K, Ca, Fe, Zn and Br degrading together — an
        # instrument event, not element noise.
        reliability = self.element_reliability(df_qc)
        self._element_reliability = reliability
        # Watch only elements that are both measured well here AND have a
        # published detection limit — the rule compares against that limit, so
        # without one there is nothing to test against.
        trusted = [e for e in reliability.index
                   if reliability.loc[e, 'verdict'] == 'quantitative'
                   and reliability.loc[e, 'published_limit']]
        mdl = self.manual_mdl()

        if trusted:
            high_uncertainty = Series(False, index=df_qc.index)
            for element in trusted:
                value = to_numeric(df_qc[element], errors='coerce')
                sigma = to_numeric(df_qc[f'{element}_uncert'], errors='coerce')
                high_uncertainty |= (
                    (value >= mdl.get(element, 0)) & (sigma > 0)
                    & (value < self.DETECTION_SIGMA * sigma)
                ).fillna(False)

            qc.add_rules([
                QCRule(
                    name='High Uncertainty',
                    condition=lambda df, mask=high_uncertainty: mask.reindex(df.index).fillna(False),
                    description=(
                        f'A normally-quantitative element reported above its detection '
                        f'limit with < {self.DETECTION_SIGMA} sigma confidence '
                        f'(watching: {", ".join(trusted)})'
                    ),
                    # Advisory: the reading is suspect but the rest of the row's
                    # 45 elements are not, and masking is per row.
                    severity=WARNING,
                ),
            ])

        # Add Internal Standard Drift rule (Nb)
        if self.INTERNAL_STD_ELEMENT in df_qc.columns:
            nb_median = df_qc[self.INTERNAL_STD_ELEMENT].median()
            lower_bound = nb_median * (1 - self.INTERNAL_STD_TOLERANCE)
            upper_bound = nb_median * (1 + self.INTERNAL_STD_TOLERANCE)
            qc.add_rules([
                QCRule(
                    name='Internal Std Drift',
                    condition=lambda df, lb=lower_bound, ub=upper_bound: (
                            (df[self.INTERNAL_STD_ELEMENT] < lb) | (df[self.INTERNAL_STD_ELEMENT] > ub)
                    ),
                    description=f'{self.INTERNAL_STD_ELEMENT} internal standard outside ±{int(self.INTERNAL_STD_TOLERANCE * 100)}% of median ({nb_median:.2f} ng/m³)'
                ),
            ])

        # Apply all QC rules and get flagged DataFrame
        df_qc = qc.apply(df_qc)

        # Log QC summary
        self.log_qc_summary(qc.get_summary(df_qc))

        self.log_below_mdl(df_qc, self.MDL)
        self._report_element_reliability(reliability)

        return df_qc.reindex(_index)

    def _report_element_reliability(self, reliability) -> None:
        """Log the per-element verdicts and write them next to the other outputs.

        The sidecar is the actionable artifact: it tells you which of the 45
        columns to build a time series from, which to treat as indicative, and
        which are noise the instrument reports because it was configured to.
        """
        if reliability.empty:
            return

        counts = reliability['verdict'].value_counts()
        self.logger.info(
            f"{self.nam} element reliability: "
            + ', '.join(f'{n} {verdict}' for verdict, n in counts.items()))
        for verdict in ('quantitative', 'semi-quantitative'):
            members = list(reliability.index[reliability['verdict'] == verdict])
            if members:
                self.logger.info(f"  {verdict}: {', '.join(members)}")
        unusable = list(reliability.index[reliability['verdict'] == 'below-detection'])
        if unusable:
            self.logger.info(
                f"  below detection ({len(unusable)}): {', '.join(unusable[:12])}"
                + (' ...' if len(unusable) > 12 else ''))
        unpublished = list(reliability.index[~reliability['published_limit']
                                             & (reliability['verdict'] != 'below-detection')])
        if unpublished:
            self.logger.info(
                f"  measured but no published detection limit: {', '.join(unpublished)}")

        path = self._output_folder / f'{self._output_prefix}_element_reliability.csv'
        try:
            reliability.to_csv(path)
            self.logger.info(f"Saved: {path.name}")
        except OSError as e:
            self.logger.warning(f"Could not write {path.name}: {e}")

    def decode_alarm(self, alarm_code):
        """Decode ALARM code to human-readable message.

        Parameters
        ----------
        alarm_code : int
            The ALARM code from the Xact data

        Returns
        -------
        str
            Human-readable description of the alarm
        """
        if alarm_code == 0:
            return 'Normal'
        elif alarm_code in self.ERROR_CODES:
            return self.ERROR_CODES[alarm_code]
        elif alarm_code in self.WARNING_CODES:
            return self.WARNING_CODES[alarm_code]
        else:
            return f'Unknown Alarm ({alarm_code})'
