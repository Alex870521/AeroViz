import csv
import re
from io import StringIO

import numpy as np

from AeroViz.dataProcess.SizeDistr._size_dist import bin_widths
from pandas import Series, read_csv, to_datetime, to_numeric

from AeroViz.rawDataReader.core import AbstractReader, QCRule, QCFlagBuilder, WARNING
from AeroViz.rawDataReader.core.size_grid import (
    DEFAULT_CHANNELS_PER_DECADE, channel_label, lattice_channels, label_range)
from AeroViz.rawDataReader.script._size_dist_output import finalize_size_dist
from AeroViz.dataProcess.SizeDistr.units import (
    DN_DLOGDP, FILE_UNIT_ATTR, parse_export_unit, to_dndlogdp)


class Reader(AbstractReader):
    """SMPS (Scanning Mobility Particle Sizer) Data Reader

    A specialized reader for SMPS data files, which measure particle size distributions
    in the range of 11.8-593.5 nm.

    See ``docs/api/instruments/particle-sizers/SMPS.md`` for usage and
    ``docs/guide/reader-reference.md`` for the
    file layout, status codes and QC rules.
    """
    nam = 'SMPS'

    # The scan period is an operator setting (AIM 10.3 ran 6-minute scans at
    # TCLab; AIM 11.x offers 1 / 5 / 10 minutes), so one folder can hold
    # several on purpose. Keep each period on its own grid.
    PIECEWISE_FREQ = True

    # =========================================================================
    # QC Thresholds
    # =========================================================================
    # Hourly completeness is a *fraction* (`hourly_completeness_QC`'s
    # threshold=0.5), not a fixed count: the expected points per hour follow the
    # frequency detected from the files. A `MIN_HOURLY_COUNT = 5` constant used to
    # sit here, never read and true only for a 6-minute grid.
    # Plausibility bounds on the integrated total, in #/cm³. These are a coarse
    # backstop — the physical limit is per-bin and lives in `CPC Over-range`.
    # Both are overridable per run: `min_total_conc=` / `max_total_conc=`.
    #
    # ⚠️ `MIN_TOTAL_CONC` was 2000 until 2026-09-09, which made the reader
    # unusable at any clean site: EBAS background stations sit at 50–300 /cm³
    # (Zeppelin's median is 95), so 99–100% of their record was being rejected
    # as invalid. A minimum is there to catch "instrument off / no flow", which
    # reads ~0, not to encode an urban site's typical loading.
    #
    # ⚠️ `MAX_TOTAL_CONC` was 1e7, which caught 19% of the scans a five-station
    # TCLab audit found implausible; measured against the same set, 1e6 catches
    # 30% and is still above any credible ambient total (roadside peaks reach
    # 2–5e5). The rest is the CPC and shape rules' job, not this one's.
    MIN_TOTAL_CONC = 10
    MAX_TOTAL_CONC = 1e6
    MAX_LARGE_BIN_CONC = 4000      # Maximum concentration for >400nm bins (DMA water ingress indicator)
    LARGE_BIN_THRESHOLD = 400      # Size threshold for large bin filter (nm)
    # A scan whose counts all sit below (smallest bin x this factor) while every
    # bin above is exactly zero never came from a full DMA voltage ramp. 2x the
    # smallest bin is 23.6 nm on the standard 11.8-593.5 nm grid.
    TRUNCATED_SCAN_FACTOR = 2.0
    #: The long-DMA window every TCLab station has recorded since 2018, as
    #: AIM 10.3 prints it. The default span for QC totals and the default
    #: reference window a file must span (`_pick_reference_window`).
    STANDARD_WINDOW = (11.8, 593.5)

    # =========================================================================
    # Status columns across AIM versions
    # =========================================================================
    # The same information is reported under DIFFERENT COLUMN NAMES depending on
    # the host software, so the reader checks every dialect it knows and ORs the
    # error masks of whichever columns are present. Verified against the corpus:
    #
    #   AIM 10.3 (.TXT)          AIM 11.x (.CSV)         OK value
    #   ----------------------   ---------------------   -----------------------
    #   Status Flag              Detector Status         'Normal Scan' (positive
    #                                                    sentinel)
    #   Instrument Errors        Classifier Errors       empty; some sites write
    #                                                    'Normal Scan' instead
    #   —                        Communication Status    '0'
    #   —                        Neutralizer Status      'ON'
    #
    # Two shapes of value: a *positive sentinel* column, OK when it equals a
    # known-good string; and an *error-token* column, OK when empty, otherwise
    # carrying one or more comma-separated fault names ('Low aerosol flow',
    # 'Neutralizer not active'). Whitelist benign tokens per site with
    # `ignored_status_errors=[...]` rather than editing raw files.
    #
    # An AIM 11.x export has NEITHER of the 10.3 names, so before this list
    # existed its `Status Error` rule could never fire — every scan passed the
    # status check regardless of what the instrument reported.
    STATUS_SPECS = (
        # (column, ok_value, extra tokens always treated as OK)
        ('Status Flag', 'Normal Scan', ()),
        ('Instrument Errors', '', ('Normal Scan',)),
        ('Detector Status', 'Normal Scan', ()),
        ('Classifier Errors', '', ('Normal Scan',)),
        ('Communication Status', '0', ()),
        ('Neutralizer Status', 'ON', ()),
    )

    #: Metadata fields naming the CPC that did the counting. Captured from the
    #: block above the data header and reported in `df.attrs`; the CPC's cut-off
    #: sets how far the lowest size channels under-report.
    #: `CPC Model` is the AIM 10.3 spelling of `Detector Model`; without it the
    #: whole 10.3 dialect reported no detector at all, which also left the
    #: `CPC Over-range` rule below permanently inert on those files.
    DETECTOR_FIELDS = ('Detector Model', 'CPC Model', 'Detector S/N', 'Nano Enhancer')
    # Preamble values of a dN/dlogDp export (AIM writes dw/dlogDp or dW/dlogDp).
    EXPECTED_UNITS = 'dW/dlogDp'
    EXPECTED_WEIGHT = 'Number'

    #: Rated maximum concentration per CPC model (#/cm³) — the top of the range
    #: over which the counter's accuracy is specified. Above it the coincidence
    #: correction is extrapolation, so a bin reading higher is not trustworthy.
    #:
    #: ⚠️ This is a *per-bin* limit, not a limit on the integrated total: the
    #: DMA passes one narrow mobility band at a time, so the counter only ever
    #: sees a slice of the distribution. Comparing it against the total is a
    #: category error — see `_cpc_bin_ceiling`.
    #:
    #: Models absent here leave the rule inert (logged, not silently skipped).
    #: Override or extend with `cpc_max_conc={'3022': 1e7}`.
    CPC_MAX_CONC = {
        '3750': 1.0e5,    # single-count with live coincidence correction
        '3772': 1e4,      # single-count only, no photometric mode
        '3787': 2.5e5,
        '3788': 4.0e5,
        '3022': 1.0e7,    # photometric above ~1e4; effectively unconstrained here
        '3022A': 1.0e7,
    }

    #: Air mean free path (nm) at the SMPS reference state (296.15 K,
    #: 101.3 kPa). Only used when a file does not record its own.
    REFERENCE_MEAN_FREE_PATH_NM = 67.3

    # Kept for backwards compatibility with callers that referenced these.
    STATUS_COLUMN = 'Status Flag'
    STATUS_OK = 'Normal Scan'
    SECONDARY_STATUS_COLUMN = 'Instrument Errors'

    # =========================================================================
    # AIM-version reconciliation (10.3 .TXT vs 11.x .CSV exports)
    # =========================================================================
    # The same physical SMPS exports different-looking size-bin headers
    # depending on the host software (AIM 10.3: 11.8–593.5 nm, one decimal;
    # AIM 11.x: 11.34–615.27 nm, two decimals) AND re-labels many metadata
    # columns. Two separate problems:
    #
    # 1. Bin labels — every 64-channel/decade export sits on one fixed
    #    lattice (see `core/size_grid.py`); the versions differ only in the
    #    digits printed and in which window of the lattice they report.
    #    `_raw_reader` renames each file's bins to the canonical label of
    #    their lattice channel, so files of any version and any scan range
    #    concatenate into one frame: shared channels line up, channels a file
    #    did not measure stay NaN. Values are never interpolated. Only a file
    #    that is NOT on that lattice (another resolution, a damaged header) is
    #    a foreign grid — `_partition_compatible_scans` keeps the dominant
    #    group and drops the rest with a warning.
    # 2. AIM-version metadata column drift — `METADATA_ALIASES` rewrites the
    #    older AIM (≤ 10.2, `Sheath Flow(lpm)` style) and AIM 11.x forms to the
    #    AIM 10.3 form on every parsed file, so a folder of any version (or a
    #    partitioned-down folder) produces a consistent schema downstream.
    #    Only the unambiguous 1:1 physical quantities are renamed; cuts that
    #    have NO 10.3 equivalent (AIM 11.x 4-way error split, granular DMA
    #    timings, ...) keep their own names because collapsing them would lose
    #    information. Left alone on purpose: old `td(s)` (10.3 writes both
    #    `td (s)` and `td + 0.5 (s)`, so which one it is isn't certain) and old
    #    `Scan Up Time(s)` vs 10.3 `Scan Time (s)`.
    METADATA_ALIASES = {
        # AIM ≤ 10.2 name -> AIM 10.3 canonical (mostly unit/spacing changes)
        'Sheath Flow(lpm)': 'Sheath Flow (L/min)',
        'Aerosol Flow(lpm)': 'Aerosol Flow (L/min)',
        'Bypass Flow(lpm)': 'Bypass Flow (L/min)',
        'CPC Inlet Flow(lpm)': 'Detector Inlet Flow (L/min)',   # CPC -> Detector, as AIM 11.x
        'CPC Sample Flow(lpm)': 'Detector Sample Flow (L/min)', # AIM 10.3 header field name
        'Retrace Time(s)': 'Retrace Time (s)',
        'Low Voltage': 'Low Voltage (V)',
        'High Voltage': 'High Voltage (V)',
        'Lower Size(nm)': 'Lower Size (nm)',
        'Upper Size(nm)': 'Upper Size (nm)',
        'Density(g/cc)': 'Density (g/cm)',
        'tf(s)': 'tf (s)',
        'D50(nm)': 'D50 (nm)',
        'Median(nm)': 'Median (nm)',
        'Mean(nm)': 'Mean (nm)',
        'Geo. Mean(nm)': 'Geo. Mean (nm)',
        'Mode(nm)': 'Mode (nm)',
        # AIM 11.x name -> AIM 10.3 canonical
        'Total Concentration (#/cm³)': 'Total Conc. (#/cm)',
        'Aerosol Temperature (C)': 'Sample Temp (C)',
        'Aerosol Humidity (%)': 'Relative Humidity (%)',
        'Aerosol Density (g/cm³)': 'Density (g/cm)',
        'Impactor D50 (nm)': 'D50 (nm)',
        'Test Name': 'Title',
        'Geo. Std. Dev': 'Geo. Std. Dev.',                       # AIM 11.x drops the trailing period
        'DMA Column transit time Tf (s)': 'tf (s)',
        'DMA Exit to Optical Detector Td (s)': 'td + 0.5 (s)',   # AIM 10.3 also adds the +0.5 offset; treated as same quantity
    }

    #: The `³` in `(#/cm³)` / `(g/cm³)` does not survive every export's
    #: encoding: depending on the AIM version and code page it is dropped,
    #: written as `?` or a space, and sometimes takes the closing parenthesis
    #: with it. Each pattern catches every spelling seen in the field
    #: (`Total Conc.(#/cm)`, `Total Conc.(#/cm?)`, `Total Conc. (#/cm?`,
    #: `Total Concentration(#/cm)`, `Density (g/cm?` ...).
    METADATA_PATTERNS = (
        (re.compile(r'^Total Conc(?:\.|entration)\s*\(#/cm.?\)?$'), 'Total Conc. (#/cm)'),
        (re.compile(r'^Density\s*\(g/c[mc].?\)?$'), 'Density (g/cm)'),
    )

    #: Aerosol (polydisperse) flow into the DMA, by AIM version. AIM 11.x has
    #: no `Aerosol Flow` column; on the 3082 classifier that flow is the one
    #: measured at the impactor.
    AEROSOL_FLOW_COLUMNS = ('Aerosol Flow (L/min)', 'Impactor Flow (L/min)')
    SHEATH_FLOW_COLUMN = 'Sheath Flow (L/min)'

    #: Per-file attr: True when the file's bins were mapped onto the standard
    #: lattice (and so carry canonical labels). Rides through the parse cache.
    ON_LATTICE_ATTR = 'smps_on_lattice'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        #: `{field: value}` scraped from the file metadata; see DETECTOR_FIELDS.
        self._detector = {}

    @classmethod
    def _inventory_sniff(cls, file):
        """AIM version, export layout and bin grid from the header block only.

        Row-oriented exports (one scan per line) are what the parser reads; a
        column-oriented export (AIM 10.x "transposed", one scan per column) is
        skipped by it, so flagging the layout here is what makes a folder of
        unreadable scans visible before a read.
        """
        delimiter = '\t' if file.suffix.lower() == '.txt' else ','
        out = {'format': 'AIM 11.x CSV' if delimiter == ',' else 'AIM 10.x TXT'}
        with open(file, 'r', encoding='utf-8', errors='ignore') as fh:
            lines = [fh.readline() for _ in range(400)]
        header = next((i for i, l in enumerate(lines)
                       if l.split(delimiter)[0].strip() in ('Sample #', 'Scan Number')), None)
        if header is None:
            out['layout'] = 'no header'
            return out
        cells = [c.strip() for c in lines[header].rstrip('\r\n').split(delimiter)]
        if any(c in ('Date', 'DateTime Sample Start') for c in cells):
            out['layout'] = 'rows'
            bins = [float(c) for c in cells if c.replace('.', '', 1).isdigit()]
        else:
            # Column-oriented: one diameter per line. Take the longest run of
            # consecutive numeric first cells — a file can also carry a one-scan
            # row-oriented block whose data line starts with the scan number.
            out['layout'] = 'columns'
            bins, run = [], []
            for l in lines[header + 1:]:
                first = l.split(delimiter)[0].strip()
                if first.replace('.', '', 1).isdigit():
                    run.append(float(first))
                else:
                    bins, run = (run if len(run) > len(bins) else bins), []
            bins = run if len(run) > len(bins) else bins
        if bins:
            out['bins'] = len(bins)
            out['grid'] = f'{min(bins):g}-{max(bins):g}'
        for l in lines[:header]:
            key, _, value = l.partition(delimiter)
            if key.strip() in cls.DETECTOR_FIELDS and value.strip():
                out.setdefault('detector', value.split(delimiter)[0].strip())
        return out

    # The CPC fields are scraped from each file's preamble while parsing. On a
    # parse-cache hit `_raw_reader` never runs, so they travel with the cached
    # frame instead (see core/parse_cache.py).
    def _collect_parse_meta(self) -> dict:
        return {'detector': dict(self._detector)} if self._detector else {}

    def _apply_parse_meta(self, meta: dict) -> None:
        for key, value in (meta.get('detector') or {}).items():
            self._detector.setdefault(key, value)

    def __call__(self, start=None, end=None, mean_freq=None):
        """Return the dN/dlogDp distribution; write S/V + a stats sidecar.

        The parent pipeline produces the QC-applied, resampled dN/dlogDp frame
        (diameters in nm as columns) and stamps ``df.attrs``. We then write the
        number / surface / volume distributions and a QC-aligned statistics file
        next to the main output. Pass ``append_stats=True`` to also append the
        statistics columns to the returned frame (default keeps it a clean PSD
        matrix for ``psd_stats`` / ``merge_psd`` / ``SizeDist``).
        """
        dist = super().__call__(start, end, mean_freq)
        dist = finalize_size_dist(self, dist, unit='nm')

        # Which CPC counted these particles, for whoever reads the data later.
        if self._detector:
            dist.attrs.update({f'cpc_{k.lower().replace(" ", "_").replace("/", "_")}': v
                               for k, v in self._detector.items()})
        return dist

    def _raw_reader(self, file):
        """Read and parse raw SMPS data files.

        Returns all columns from the raw file. Column selection is deferred
        to _QC() and _process() stages.

        Supported formats:
        - S80 TXT (AIM old): tab-separated, header at 'Sample #'
        - S82 TXT (AIM 10.3): tab-separated, header at 'Sample #'
        - CSV (AIM 11.x): comma-separated, header at 'Scan Number'
        """

        export = {}  # Units / Weight from the preamble

        def find_header_row(file_obj, delimiter):
            """Locate the data header, capturing the detector metadata above it.

            The block before the header names the CPC doing the counting
            (`Detector Model`, `Nano Enhancer`). That decides where the counting
            efficiency rolls off, and therefore how far the lowest channels
            under-report — see `docs/theory/counting_efficiency.md`. The CPC is a
            separate instrument that can be swapped, so it is worth recording
            which one produced a given dataset rather than assuming.
            """
            csv_reader = csv.reader(file_obj, delimiter=delimiter)
            for skip, row in enumerate(csv_reader):
                if row and (row[0] in ['Sample #', 'Scan Number']):
                    return skip
                # AIM 11.x CSV puts one field per line; AIM 10.3 TXT packs
                # several key/value pairs onto one tab-separated line, so walk
                # the whole row rather than just its first cell.
                for key, value in zip(row[::2], row[1::2]):
                    if key.strip() in self.DETECTOR_FIELDS and value.strip():
                        self._detector.setdefault(key.strip(), value.strip())
                    if key.strip() in ('Units', 'Weight', 'Channels/Decade') and value.strip():
                        export.setdefault(key.strip(), value.strip())
            raise ValueError("Header row not found")

        def parse_date(df, date_format):
            if 'Date' in df.columns and 'Start Time' in df.columns:
                return to_datetime(df['Date'] + ' ' + df['Start Time'], format=date_format, errors='coerce')
            elif 'DateTime Sample Start' in df.columns:
                return to_datetime(df['DateTime Sample Start'], format=date_format, errors='coerce')
            else:
                raise ValueError("Expected date columns not found")

        if file.suffix.lower() == '.txt':
            # %Y/%m/%d for AIM 10.3+ which exports dates like "2021/1/3"
            delimiter, date_formats = '\t', ['%m/%d/%y %X', '%m/%d/%Y %X', '%Y/%m/%d %X']
        else:  # csv
            delimiter, date_formats = ',', ['%d/%m/%Y %X']

        # Read the file once. The header scan used to run csv.reader over the
        # open file and then seek(0) for read_csv — two passes over the preamble
        # per file, about 7 ms each across a year of daily exports. Scanning the
        # in-memory lines and handing read_csv the remainder parses the same
        # bytes with the same options, so the result is identical.
        with open(file, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.read().splitlines(keepends=True)
        skip = find_header_row(iter(lines), delimiter)

        # Everything downstream treats the bins as dN/dlogDp. AIM can also
        # export per channel ("Concentration (dW)"), surface / volume / mass
        # weighting, or % concentration. The first ones convert exactly and are
        # converted below; % cannot be undone without the total, so it is
        # skipped loudly. A preamble without these fields is taken as dN/dlogDp.
        units, weight = export.get('Units'), export.get('Weight')
        export_unit = parse_export_unit(units, weight if weight is not None else
                                        (None if units is None else 'Number'))
        # Mass weighting: no SMPS mass export exists to verify AIM's mass unit
        # against, so it is not converted on an assumed one (see `to_dndlogdp`).
        if export_unit is not None and export_unit.moment == 'M':
            export_unit = None
        if export_unit is None:
            self.logger.warning(
                f"{file.name}: exported as Units={units}, Weight={weight}, which "
                f"cannot be converted to {DN_DLOGDP}; skipped. Re-export it from "
                f"AIM as {self.EXPECTED_UNITS}, {self.EXPECTED_WEIGHT} weighting.",
                group='unit_skipped', item=file.name, detail=f'Units={units}, Weight={weight}')
            return None

        with StringIO(''.join(lines[skip:])) as f:
            _df = read_csv(f, sep=delimiter, low_memory=False)
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
            comma_decimal_cols = [col for col in _df.columns if isinstance(col, str) and ',' in col.strip()]
            if comma_decimal_cols:
                self.logger.warning(f"Detected {len(comma_decimal_cols)} columns using comma as decimal separator")
                _df.columns = _df.columns.str.replace(',', '.')

            # Identify size bin columns (numeric column names)
            numeric_cols = [col for col in _df.columns if isinstance(col, str) and col.strip().replace('.', '').isdigit()]
            numeric_cols.sort(key=lambda x: float(x.strip()))

            # Set time index
            _df.index = _time_index
            _df.index.name = 'time'
            _df = _df.loc[_df.index.dropna().copy()]

            # Rename size bin columns to float values. A file on the standard
            # 64-channel/decade lattice gets the canonical label of each
            # channel (AIM 11.x `11.76` -> `11.8`; an AIM <= 10.3 file is
            # already canonical), which is what lets exports of different AIM
            # versions and scan ranges share columns. Anything else keeps the
            # labels it was printed with.
            bin_rename = {col: float(col.strip()) for col in numeric_cols}
            file_cpd = to_numeric(export.get('Channels/Decade'), errors='coerce')
            if not np.isfinite(file_cpd):
                file_cpd = DEFAULT_CHANNELS_PER_DECADE
            lattice_k = (lattice_channels(bin_rename.values())
                         if file_cpd == DEFAULT_CHANNELS_PER_DECADE else None)
            if lattice_k is not None:
                bin_rename = {col: channel_label(k) for col, k in zip(bin_rename, lattice_k)}
            _df = _df.rename(columns=bin_rename)
            bin_cols = sorted(bin_rename.values())

            # Check size range — only reject when user explicitly requested a specific range.
            # Otherwise just warn so older instrument configs (e.g. 2017 with 18.8-914 nm)
            # still get parsed for coverage / time-index purposes.
            explicit_range = self.kwargs.get('size_range')
            if explicit_range is not None and lattice_k is not None:
                explicit_range = self._canonical_range(explicit_range)
            size_range = explicit_range or (11.8, 593.5)
            if bin_cols[0] != size_range[0] or bin_cols[-1] != size_range[1]:
                self.logger.warning(f'SMPS file: {file.name} size range mismatch. '
                                    f'Expected {size_range}, got ({bin_cols[0]}, {bin_cols[-1]})',
                                    group='grid', item=file.name,
                                    detail=f'{bin_cols[0]:g}–{bin_cols[-1]:g} nm',
                                    expected=f'{size_range[0]:g}–{size_range[1]:g} nm')
                if explicit_range is not None:
                    return None

            # Drop columns already consumed for the time index
            index_cols = ['Date', 'Start Time', 'DateTime Sample Start',
                          'Sample #', 'Scan Number', 'Diameter Midpoint', 'Diameter Midpoint (nm)']
            _df = _df.drop(columns=[c for c in index_cols if c in _df.columns], errors='ignore')

            # AIM ≤ 10.2 / 11.x → AIM 10.3 metadata canonicalization so consumers
            # see the same column names regardless of which host software
            # exported the file. Only the unambiguous 1:1 physical quantities are
            # renamed — see `METADATA_ALIASES` docstring above. A pre-existing
            # AIM 10.3 column with the same canonical name is rare in practice
            # (the file is one AIM version or the other), but if it happens we
            # keep the 10.3 form and drop the other duplicate.
            rename = {old: new for old, new in self.METADATA_ALIASES.items()
                      if old in _df.columns}
            for col in _df.columns:
                if isinstance(col, str) and col not in rename:
                    new = next((name for pat, name in self.METADATA_PATTERNS
                                if pat.match(col.strip())), None)
                    if new is not None and new != col:
                        rename[col] = new
            if rename:
                drop_dup = [old for old, new in rename.items() if new in _df.columns]
                if drop_dup:
                    _df = _df.drop(columns=drop_dup)
                    rename = {k: v for k, v in rename.items() if k not in drop_dup}
                if rename:
                    _df = _df.rename(columns=rename)

            _df = _df.loc[~_df.index.duplicated() & _df.index.notna()]

            # Bring a per-channel / surface / volume / mass export to dN/dlogDp,
            # and record what it was so the output can say so (the per-file
            # attrs ride along through the parse cache).
            if export_unit.label != DN_DLOGDP:
                channels = to_numeric(export.get('Channels/Decade'), errors='coerce')
                density = (to_numeric(_df['Density (g/cm)'], errors='coerce').to_numpy()
                           if 'Density (g/cm)' in _df.columns else None)
                _df[bin_cols] = to_dndlogdp(
                    _df[bin_cols], export_unit, dp_unit='nm', density=density,
                    dlogdp=1.0 / channels if channels and channels > 0 else None)
                self.logger.info(f"{file.name}: converted {export_unit.label} to {DN_DLOGDP}",
                                 group='converted', item=file.name, detail=export_unit.label)
            _df.attrs[FILE_UNIT_ATTR] = export_unit.label
            _df.attrs[self.ON_LATTICE_ATTR] = lattice_k is not None
            return _df

    @staticmethod
    def _canonical_range(size_range):
        """`size_range` ends as canonical lattice labels.

        Callers name a range by the diameters their AIM version printed
        (`(11.34, 615.27)` for AIM 11.x); the columns carry canonical labels
        (`11.3`, `615.3`). Ends that are not on the lattice are left alone.
        """
        channels = lattice_channels(size_range)
        if channels is None:
            return tuple(size_range)
        return tuple(channel_label(k) for k in channels)

    @classmethod
    def _bin_signature(cls, df):
        """Which grid a file belongs to, for `_partition_compatible_scans`.

        Every file on the standard lattice shares one signature whatever its
        scan range — their columns are the same channels under the same
        labels, so they concatenate cleanly. A file off the lattice is
        fingerprinted by its own sorted bin tuple (rounded to 2 decimals so
        float jitter does not split identical grids).
        """
        if df.attrs.get(cls.ON_LATTICE_ATTR):
            return ('lattice', DEFAULT_CHANNELS_PER_DECADE)
        return tuple(sorted(round(float(c), 2)
                            for c in df.columns if isinstance(c, (int, float))))

    @staticmethod
    def _bin_labels(df):
        return sorted(float(c) for c in df.columns if isinstance(c, (int, float)))

    def _partition_compatible_scans(self, df_list, files):
        """Keep the files that can stand in one record; drop the rest, by name.

        Two independent reasons a file is left out, both reported as
        `grid_skipped` with the file names so nothing disappears quietly:

        1. **Foreign grid.** Files on the standard lattice always go together
           (see `_bin_signature`); a file off it (another channels-per-decade
           setting, a damaged header) cannot share their columns. The group
           with the most rows wins — rows, not files, so a swarm of tiny
           files cannot outvote one large typical one.
        2. **Narrower window.** Among lattice files, one whose scan range does
           not span the record's reference window (`_pick_reference_window`)
           is a different measurement — a nano-DMA test, a shortened range.
           Left in, its scans would sit in the record with most channels
           empty, drag every total and mean diameter down, and take the time
           slot of a full scan recorded alongside it.

        Everything else is read whole: AIM 10.3 next to AIM 11.x, a window
        wider than the reference. The windows mixed are listed so the
        wider-than-usual frame is not a surprise.
        """
        groups: dict = {}
        for f, df in zip(files, df_list):
            groups.setdefault(self._bin_signature(df), []).append((f, df))

        def total_rows(items):
            return sum(len(df) for _, df in items)

        def skip(items, reason, detail):
            names = [f.name for f, _ in items]
            shown = ', '.join(names[:5]) + (f', ... (+{len(names) - 5} more)' if len(names) > 5 else '')
            self.logger.warning(
                f"Mixed-format SMPS folder: skipping {len(names)} file(s) "
                f"({total_rows(items)} rows) {reason}. Files: {shown}. "
                f"Move them to a separate folder to process them in their own run.",
                group='grid_skipped', items=names, detail=detail)

        sigs_ranked = sorted(groups.items(), key=lambda kv: total_rows(kv[1]), reverse=True)
        dominant_sig, kept_items = sigs_ranked[0]
        kept_labels = sorted({c for _, df in kept_items for c in self._bin_labels(df)})

        for sig, items in sigs_ranked[1:]:
            labels = sorted({c for _, df in items for c in self._bin_labels(df)})
            skip(items,
                 f"whose size bins ({label_range(labels)}) are on a different grid than "
                 f"the dominant group ({label_range(kept_labels)}) and cannot share its columns",
                 label_range(labels))

        n_before = len(kept_items)
        if dominant_sig and dominant_sig[0] == 'lattice':
            self._reference_window = ref = self._pick_reference_window(
                [df for _, df in kept_items])
            windows: dict = {}
            for item in kept_items:
                labels = self._bin_labels(item[1])
                if labels:
                    windows.setdefault((labels[0], labels[-1]), []).append(item)
            if ref is not None:
                for (lo, hi), items in windows.items():
                    if lo > ref[0] or hi < ref[1]:
                        skip(items,
                             f"whose scan range ({lo:g}–{hi:g} nm) does not span this "
                             f"record's {ref[0]:g}–{ref[1]:g} nm window",
                             f'{lo:g}–{hi:g} nm')
                windows = {w: items for w, items in windows.items()
                           if w[0] <= ref[0] and w[1] >= ref[1]}
                kept_items = [item for items in windows.values() for item in items]
            if len(windows) > 1:
                ranked = sorted(windows.items(), key=lambda kv: len(kv[1]), reverse=True)
                breakdown = ', '.join(f'{lo:g}–{hi:g} nm ({len(items)} file(s))'
                                      for (lo, hi), items in ranked)
                self.logger.info(
                    f"SMPS files cover different size ranges on the same channel "
                    f"lattice: {breakdown}. All kept; a channel is NaN where a "
                    f"file did not measure it.",
                    group='grid_windows', detail=breakdown)

        # Nothing dropped: hand back the caller's own list.
        if len(groups) == 1 and len(kept_items) == n_before:
            return df_list
        keep = {id(df) for _, df in kept_items}
        return [df for df in df_list if id(df) in keep]

    def _pick_reference_window(self, df_list):
        """The size window a file must span to stand in this record: ``(lo, hi)``.

        - an explicit ``size_range=``, else
        - the standard 11.8–593.5 nm window when the folder's dominant window
          (by rows) covers it — so AIM 10.3 and the wider AIM 11.x both pass,
          whichever happens to hold more rows, else
        - the dominant window itself (an archive recorded on another range,
          e.g. 18.8–914 nm, is its own reference).
        """
        explicit = (getattr(self, 'kwargs', None) or {}).get('size_range')
        if explicit is not None:
            return self._canonical_range(explicit)
        rows: dict = {}
        for df in df_list:
            labels = self._bin_labels(df)
            if labels:
                key = (labels[0], labels[-1])
                rows[key] = rows.get(key, 0) + len(df)
        if not rows:
            return None
        dominant = max(rows, key=rows.get)
        lo, hi = self.STANDARD_WINDOW
        return (lo, hi) if dominant[0] <= lo and dominant[1] >= hi else dominant

    def _flow_ratio(self, _df):
        """Per-scan aerosol/sheath flow ratio β, or ``None`` if the flows are absent.

        Flows are read under their canonical (AIM 10.3) names — `_raw_reader`
        renames the older and newer AIM spellings. This used to look up
        `Aerosol Flow(lpm)` only, which left the CPC over-range rule inert on
        every AIM 10.3 / 11.x export.
        """
        qa_col = next((c for c in self.AEROSOL_FLOW_COLUMNS if c in _df.columns), None)
        if qa_col is None or self.SHEATH_FLOW_COLUMN not in _df.columns:
            return None
        qa = to_numeric(_df[qa_col], errors='coerce')
        qsh = to_numeric(_df[self.SHEATH_FLOW_COLUMN], errors='coerce')
        ratio = (qa / qsh).replace([np.inf, -np.inf], np.nan)
        if not ratio.notna().any():
            return None
        return ratio.fillna(ratio.median()).to_numpy()

    @classmethod
    def _rated_max_conc(cls, model: str):
        """Look up a counter's rated maximum from a free-text model string.

        The field is whatever the operator's software wrote — `3772`,
        `3788 Low Flow`, `3022A` — so match on the longest known key contained
        in it rather than requiring equality. Longest-first matters: `3022A`
        must not be answered by the `3022` entry when both are listed.

        Returns ``None`` when nothing matches, which leaves the rule inert.
        """
        if not model:
            return None
        for key in sorted(cls.CPC_MAX_CONC, key=len, reverse=True):
            if key in model:
                return cls.CPC_MAX_CONC[key]
        return None

    def _cpc_bin_ceiling(self, dp, beta, cpc_max, mean_free_path_nm=None):
        """Highest credible ``dN/dlogDp`` per bin before the CPC is over-range.

        The DMA passes one narrow mobility band at a time, so the counter sees

            N_counted(Dp) ~ dN/dlogDp(Dp) x dlog10(Dp)_transfer

        and the rated maximum applies to *that*, not to the integrated total.
        Inverting gives the ceiling. The transfer function's width in mobility
        is ``beta = q_aerosol / q_sheath``; converting to diameter needs the
        local slope ``|dlnZ/dlnDp|``, which runs from ~2 in the free-molecular
        regime to ~1 in the continuum — so **the ceiling is a curve, not a
        constant**, about 40% lower at 600 nm than at 12 nm.

        A higher sheath ratio narrows the transfer function and therefore
        *raises* the ceiling: the same counter tolerates a denser aerosol when
        it only ever sees a thinner slice of it.

        Parameters
        ----------
        dp : ndarray
            Bin midpoints (nm).
        beta : float or ndarray
            Aerosol/sheath flow ratio. Scalar, or one value per scan.
        cpc_max : float
            Rated maximum concentration of the counter (#/cm³).
        mean_free_path_nm : float, optional
            Defaults to `REFERENCE_MEAN_FREE_PATH_NM`; pass the file's own
            ``Mean Free Path (m)`` when available.

        Returns
        -------
        ndarray
            Ceiling per bin — shape ``(len(dp),)`` for scalar ``beta``,
            ``(len(beta), len(dp))`` otherwise.
        """
        lam = mean_free_path_nm or self.REFERENCE_MEAN_FREE_PATH_NM
        dp = np.asarray(dp, dtype=float)

        def _log_mobility(d):
            kn = 2 * lam / d
            return np.log((1 + kn * (1.257 + 0.4 * np.exp(-1.1 / kn))) / d)

        h = 1e-4
        slope = np.abs((_log_mobility(dp * (1 + h)) - _log_mobility(dp * (1 - h))) / (2 * h))

        beta = np.asarray(beta, dtype=float)
        width = np.expand_dims(beta, -1) / (slope * np.log(10))   # dlog10(Dp) per band
        return cpc_max / width

    @staticmethod
    def _truncated_scan_mask(df_numeric, factor):
        """True where a scan has counts but nothing above ``smallest bin x factor``.

        First seen at FS from mid-2026-08: 11.8-14 nm bins carrying 1.6e4-1.2e5
        dN/dlogDp while every bin from 20 nm up reads exactly 0, total about 60 %
        of the neighbouring scans. That is a DMA ramp that never ran (or a scan
        cut short), not a nucleation burst -- a real burst still has particles
        above 20 nm. It passed every other rule: the total is inside the
        plausible range and no single bin exceeds the CPC ceiling, so on a
        heat map it is a red bar pinned to the floor and the GMD trace drops
        from ~66 nm to ~13 nm for one scan. NULL bins above count as zero:
        the instrument writes nothing there when the ramp is missing.
        """
        if df_numeric.shape[1] == 0:
            return Series(False, index=df_numeric.index)
        dp = df_numeric.columns.to_numpy(float)
        upper = df_numeric.columns[dp >= dp.min() * factor]
        if len(upper) == 0:
            return Series(False, index=df_numeric.index)
        total = df_numeric.sum(axis=1, min_count=1)
        upper_sum = df_numeric[upper].abs().sum(axis=1, min_count=1).fillna(0)
        return ((total > 0) & (upper_sum == 0)).fillna(False)

    def _QC(self, _df):
        """
        Perform quality control on SMPS particle size distribution data.

        QC Rules Applied
        ----------------
        1. Status Error        : Non-empty status flag indicates instrument error
        2. Insufficient        : Less than 50% hourly data completeness (WARNING, not dropped)
        3. Invalid Number Conc : Total number concentration outside plausible range (10-1e6 #/cm³);
                                 total = sum(dN/dlogDp x dlogDp) with per-bin widths
        4. CPC Over-range      : A bin exceeds what the counter can count (per-instrument, from the file header)
        5. DMA Water Ingress   : Bins >400nm with concentration > 4000 dN/dlogDp (indicates water in DMA)
        6. Truncated Scan      : Counts only in the smallest bins, every bin above exactly zero
                                 (the voltage ramp never completed; not a nucleation event)
        """
        _df = _df.copy()
        _index = _df.index.copy()

        # Apply size range filter
        size_range = self._canonical_range(self.kwargs.get('size_range') or self.STANDARD_WINDOW)
        numeric_cols = [col for col in _df.columns if isinstance(col, (int, float))]
        df_numeric = _df[numeric_cols]
        size_mask = (df_numeric.columns.astype(float) >= size_range[0]) & (df_numeric.columns.astype(float) <= size_range[1])
        df_numeric = df_numeric.loc[:, size_mask]

        # Total number concentration for the QC checks below: sum of dN over
        # the bins, i.e. sum(dN/dlogDp x dlogDp).
        #
        # Two bugs lived here until 2026-09-09, and both made the
        # `Invalid Number Conc` thresholds mean something other than they say:
        #   1. `np.log` (natural) was used where the data is dN/dlog10Dp, so
        #      every total came out ln(10) = 2.303x too high. `MAX_TOTAL_CONC`
        #      of 1e7 was really 4.34e6 and `MIN_TOTAL_CONC` of 2000 was 868.
        #   2. `columns[:-1]` dropped a column before diffing, averaging over
        #      n-2 gaps instead of n-1.
        # Now uses the per-bin widths (`bin_widths`) rather than a single mean
        # step, which also makes the total correct on a non-uniform grid.
        # Verified against the instrument's own `Total Conc.` column: 0.996-0.999.
        dlogDp = bin_widths(df_numeric.columns.to_numpy(float))
        total_conc = (df_numeric * dlogDp).sum(axis=1, min_count=1)

        # Get large bins (>400nm)
        large_bins = df_numeric.columns[df_numeric.columns.astype(float) >= self.LARGE_BIN_THRESHOLD]

        truncated = self._truncated_scan_mask(df_numeric, self.TRUNCATED_SCAN_FACTOR)
        truncated_above_nm = float(df_numeric.columns.min()) * self.TRUNCATED_SCAN_FACTOR if df_numeric.shape[1] else float('nan')

        min_total = self.kwargs.get('min_total_conc', self.MIN_TOTAL_CONC)
        max_total = self.kwargs.get('max_total_conc', self.MAX_TOTAL_CONC)

        # ---- CPC over-range: the counter's rated maximum, per bin -------------
        # Everything here is read from the file itself (detector model in the
        # header, flows in the data rows), so changing counter or sheath ratio
        # mid-record is picked up without configuration.
        cpc_model = str(self.kwargs.get('cpc_model')
                        or self._detector.get('CPC Model')
                        or self._detector.get('Detector Model') or '').strip()
        cpc_max = self.kwargs.get('cpc_max_conc')
        if cpc_max is None:
            cpc_max = self._rated_max_conc(cpc_model)

        beta = self._flow_ratio(_df)

        lam_nm = None
        if 'Mean Free Path (m)' in _df.columns:
            lam = to_numeric(_df['Mean Free Path (m)'], errors='coerce').median()
            if np.isfinite(lam) and lam > 0:
                lam_nm = float(lam) * 1e9

        if cpc_max is None or beta is None:
            missing = 'detector model' if cpc_max is None else 'sheath/aerosol flow'
            self.logger.debug(
                f'CPC Over-range rule inert: {missing} unavailable '
                f'(model={cpc_model or "unknown"}). Supply `cpc_max_conc=` to enable.')
            cpc_over = Series(False, index=_df.index)
        else:
            ceiling = self._cpc_bin_ceiling(
                df_numeric.columns.to_numpy(float), beta, float(cpc_max), lam_nm)
            cpc_over = Series(
                (df_numeric.to_numpy(float) > ceiling).any(axis=1), index=_df.index)

        # Build QC rules declaratively
        qc = self.qc_builder()

        # Operator-supplied whitelist of benign status tokens (e.g.
        # 'Low aerosol flow' on a known-noisy instrument). Defaults to None
        # so existing pipelines see no behavioural change.
        ignored_status_errors = self.kwargs.get('ignored_status_errors') or None

        # Warn once if this export uses none of the dialects we know, since the
        # rule below would then be permanently silent.
        status_columns = self.check_status_columns(
            _df, [name for name, _, _ in self.STATUS_SPECS])
        if status_columns:
            self.logger.debug(f"SMPS status columns in use: {', '.join(status_columns)}")

        def _combined_status_error_mask(df):
            """OR the error masks of every status column this export provides.

            Each entry in `STATUS_SPECS` names a column, the value that means OK,
            and any extra tokens to treat as OK. A column that is absent is
            skipped, so one implementation covers AIM 10.3, AIM 11.x and any
            mixed folder without configuration.

            `'Normal Scan'` is never a real error in any column, so it is
            whitelisted on the error-token columns too: most sites leave those
            empty when healthy, but some write the positive sentinel there
            instead, and without this every scan from those sites would be
            flagged.
            """
            qc_ctrl = self.QC_control()
            mask = Series(False, index=_df.index)

            for column, ok_value, extra_ok in self.STATUS_SPECS:
                if column not in _df.columns:
                    continue
                ignored = list(ignored_status_errors or []) + list(extra_ok)
                mask = mask | qc_ctrl.filter_error_status(
                    _df, status_column=column, status_type='text',
                    ok_value=ok_value, ignored_values=ignored or None,
                )

            return mask.reindex(df.index).fillna(False)

        qc.add_rules([
            QCRule(
                name='Status Error',
                condition=_combined_status_error_mask,
                description=(
                    'Instrument reported a fault in '
                    + (', '.join(f'`{c}`' for c in status_columns) if status_columns
                       else 'no recognised status column (rule inert)')
                    + (f' (ignoring: {ignored_status_errors})' if ignored_status_errors else '')
                )
            ),
            QCRule(
                name='Insufficient',
                # Judged per scan, not per bin: a scan is one measurement, and
                # in a folder mixing scan ranges a channel that one period never
                # measured would otherwise mark that whole period insufficient.
                condition=lambda df: self._hourly_completeness(
                    df[df_numeric.columns].notna().any(axis=1)
                    .astype(float).replace(0.0, np.nan).to_frame('scan')
                ),
                description='Less than 50% hourly data completeness',
                # Representativeness, not validity: the readings in a sparse
                # hour are fine, it is an average over that hour that would
                # misrepresent it. Users were losing the head and tail of
                # every read to this. Promote it per run with
                # flag_severity={'Insufficient': 'error'}.
                severity=WARNING,
            ),
            QCRule(
                name='Invalid Number Conc',
                condition=lambda df, tc=total_conc, lo=min_total, hi=max_total: Series(
                    (tc < lo) | (tc > hi), index=df.index
                ).fillna(True),
                description=f'Total number concentration outside plausible range ({min_total:g}-{max_total:.0e} #/cm³)'
            ),
            QCRule(
                name='Truncated Scan',
                condition=lambda df, m=truncated: m.reindex(df.index).fillna(False),
                description=(
                    f'Counts only below {truncated_above_nm:.1f} nm with every bin above exactly zero '
                    '(DMA voltage ramp never completed; not a nucleation event)'
                )
            ),
            QCRule(
                name='CPC Over-range',
                condition=lambda df, m=cpc_over: m.reindex(df.index).fillna(False),
                description=(
                    f'A bin exceeded what a {cpc_model or "unknown"} CPC can count '
                    f'({cpc_max:,.0f} #/cm³) given the recorded sheath ratio'
                    if cpc_max is not None and beta is not None
                    else 'CPC over-range (rule inert: detector model or flows unavailable)'
                )
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
        """Return the QC'd dN/dlogDp size bins (plus ``QC_Flag``).

        The size distribution itself is the canonical SMPS product. Summary
        statistics (total / GMD / GSD / mode, mode fractions) and the surface
        and volume distributions are *derived* quantities — compute them on
        demand with :func:`AeroViz.psd_stats` / :func:`AeroViz.psd_distributions`
        rather than baking them into the reader output. This keeps the reader's
        return type a plain dN/dlogDp DataFrame (diameters as columns), which is
        exactly what ``psd_stats`` / ``merge_psd`` / ``SizeDist`` consume.
        """
        _index = _df.index.copy()

        bin_cols = [col for col in _df.columns if isinstance(col, (int, float))]

        # Log the QC summary collected in _QC()
        if getattr(self, '_qc_summary', None) is not None:
            self.log_qc_summary(self._qc_summary)

        # Keep only the size bins + QC bookkeeping (drop the raw status column)
        return _df[bin_cols + self.qc_columns(_df)].reindex(_index)
