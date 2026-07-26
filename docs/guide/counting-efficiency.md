# Counting Efficiency (CPC & APS)

!!! warning "Recorded, not applied"
    **AeroViz does not correct for any of this.** A size distribution from
    `RawDataReader` is what the instrument reported, uncorrected. This page exists
    so the size-dependent under-counting is *known and quantified* when you use
    the data — it is a real bias at the ends of both size ranges, not a rounding
    error. Nothing here is wired into QC.

A size distribution is a counting measurement, and neither counter counts every
particle that enters it. The efficiency is size-dependent and falls off sharply
at one end of each instrument's range:

- **SMPS** — the DMA classifies, but a **CPC** does the counting. Below the CPC's
  cut-off, particles are too small to grow into detectable droplets, so the
  lowest channels under-report. Which CPC is attached decides where that happens.
- **APS** — under-counts at *both* ends: small particles fall below the optical
  detector's reliable response, large ones are lost to inlet aspiration and
  transmission before they reach the detector. Droplets fare far worse than
  solid particles.

---

## 1. CPC — which counter is attached

The SMPS raw file records this in its metadata block, above the data header:

```
Detector Model	3750	Detector S/N	3750234302	Nano Enhancer 	 None
Detector Sample Flow (L/min)	1.00	Detector Inlet Flow (L/min)	1.00
```

AIM 11.x CSV exports carry the same fields (`Detector Model`, `Detector S/N`,
`Nano Enhancer`) one per line. **Read it from your own files** rather than
assuming — the CPC is a separate instrument that can be swapped, and the cut-off
moves with it.

### Current TSI line

From TSI Application Note **CPC-002**, *Choosing the Right CPC for Your
Application* (Table 1, rev. D 2024). D50 is the diameter at which counting
efficiency reaches 50 %.

| Model | D50 (nm) | Working fluid | Sample flow (LPM) | Conc. accuracy | Pairs with SMPS 3082 |
|---|---:|---|---:|---:|:---:|
| 3007 | 10 | isopropanol | 0.1 | ±20 % | no |
| **3750** | **7** | butanol | 1.0 | ±5 % | **yes** |
| 375010 | 10 | butanol | 1.0 | ±5 % | yes |
| 3752 | 4 | butanol | 0.3 | ±5 % | yes |
| 3756 | 2.5 | butanol | 0.05 | ±10 % | yes |
| 3757-50 | 1 [^1] | DEG + butanol | 0.15 | ±10 / ±15 % | yes |
| 3783 | 7 | water | 0.12 | ±20 % | no |
| 3789 | 2.2, 7, custom [^2] | water | 0.3 | ±5 % | yes |
| 3790A | 23 | butanol | 1.0 | ±10 % | no |
| 3790A-10 | 10 | butanol | 1.0 | ±10 % | no |

[^1]: 1.4 nm electrical mobility diameter, 1.1 nm geometric; verified with NaCl.
      The 3757 is a *growth activator*, not a counter — it must be paired with a
      true CPC (e.g. the 3750 mounted on top) because its own droplets only reach
      ~100 nm.
[^2]: D50 user-selectable from the control panel.

The `375010` is the same hardware as the 3750 given a **CEN-compliant 10 nm
calibration** — same instrument, deliberately different cut-off. The `Detector
Model` field alone will not always tell you which calibration a unit carries.

### The curve, not just the cut-off

D50 is one point on a curve, and the curve is what matters for the lowest SMPS
channels. Three findings worth carrying:

**Nominal D50 is not measured D50.** Wiedensohler et al. (2012) calibrated ten
CPCs against a reference electrometer with silver particles; the TSI 3772 units
averaged a 50 % detection diameter of **7.52 ± 0.04 nm** against a nominal
10 nm. Units at the same factory settings still differed from each other by a
few nm.

**The cut-off moves with the temperature difference.** The saturator–condenser
ΔT is an operating parameter, not a constant: running at 25 °C instead of the
factory 17 °C shifts D50 to smaller sizes measurably (Wiedensohler et al. 2012,
Fig. 3 — the same model appears at both settings with visibly different curves).
If your ΔT is not the factory default, published curves for that model do not
describe your instrument.

**Output mode can bias the count.** Hermann et al. (2007) found CPC pulse outputs
under-reporting by 2–10 % relative to the serial output, requiring a ~10 %
correction for the 3776.

Hence the ACTRIS/GAW practice: calibrate the counting-efficiency curve annually
against a reference, and accept it only within **5 % on the plateau** and **1 nm
on D50** (Wiedensohler et al. 2012, §4.2 and the QC criteria in §7). The same
paper lists "correction for CPC counting efficiency" as a required processing
step for network-quality data — a correction AeroViz leaves to you.

### Curve shape

Measured curves are conventionally fitted with a saturating exponential in
diameter, of the form

$$\eta(D_p) = a\left[1 - \exp\!\left(-\frac{D_p - D_0}{D_1}\right)\right]$$

where `a` is the plateau efficiency (ideally 1), `D₀` the onset diameter and `D₁`
the width of the rise. Coefficients are **specific to the unit and its ΔT**, so
this page deliberately does not tabulate them: use the calibration certificate
for your own counter, or the curves in the reference below for the model class.

---

## 2. APS 3321 — efficiency at both ends

The APS under-counts differently: not a condensation threshold but a combination
of **aspiration losses, transmission losses and detector errors**
(Volckens & Peters, 2005).

| Particle type | Efficiency | Size dependence |
|---|---|---|
| Solid | 85–99 % | roughly flat across the range |
| Liquid droplets | 75 % → 25 % | falls steadily from 0.8 µm to 10 µm |

The droplet result is the one to remember: at 10 µm the APS counts roughly **one
droplet in four**. Ambient aerosol in the coarse mode is often at least partly
deliquesced, so which of these two rows applies to a given dataset is a judgement
about the aerosol, not a property of the instrument.

Peters & Leith (2003) characterised concentration measurement and counting
efficiency for the 3321 specifically; Pfeifer et al. (2016) intercompared 15
APS 3321 units and quantified the unit-to-unit spread in sizing and number
concentration — the counterpart to the CPC unit-to-unit variability above.

---

## 3. What this means when reading AeroViz output

- The **lowest SMPS channels** are under-counted by an amount set by your CPC's
  cut-off. With a 3750 (D50 7 nm) against an SMPS range starting at 11.8 nm, the
  first channels sit on the rising part of the curve, not the plateau.
- The **APS coarse end** is under-counted, severely so for droplets.
- An **SMPS–APS merge** therefore joins two differently-biased measurements. The
  merge in `AeroViz.merge_psd` fits and blends the overlap region; it does not
  correct either instrument's counting efficiency, so a merge inherits both.
- `df.attrs` records the instrument and its native resolution, but **not** the
  CPC model — read it from the raw file header (§1) when it matters.

## References

- TSI Inc., *Choosing the Right CPC for Your Application*, Application Note
  CPC-002 rev. D (2024) — [PDF](https://tsi.com/getmedia/c2470d2c-7fcc-4a8a-8f6c-a121efab523f/Choosing-the-Right-CPC-App-Note-CPC-002-US?ext=.pdf)
- Wiedensohler, A. et al. (2012), *Mobility particle size spectrometers:
  harmonization of technical standards and data structure…*, Atmos. Meas. Tech.
  **5**, 657–685 — [open access](https://amt.copernicus.org/articles/5/657/2012/amt-5-657-2012.pdf)
- Wiedensohler, A. et al. (2018), *Mobility particle size spectrometers:
  Calibration procedures and measurement uncertainties*, Aerosol Sci. Technol.
  **52**(2) — [DOI](https://www.tandfonline.com/doi/abs/10.1080/02786826.2017.1387229)
- Hermann, M. et al. (2007), *Particle counting efficiencies of new TSI
  condensation particle counters*, J. Aerosol Sci. **38**, 674–682 —
  [DOI](https://www.sciencedirect.com/science/article/abs/pii/S0021850207000705)
- Volckens, J. & Peters, T. M. (2005), *Counting and particle transmission
  efficiency of the aerodynamic particle sizer*, J. Aerosol Sci. **36**,
  1400–1408 — [DOI](https://www.sciencedirect.com/science/article/abs/pii/S002185020500073X)
- Peters, T. M. & Leith, D. (2003), *Concentration measurement and counting
  efficiency of the aerodynamic particle sizer 3321*, J. Aerosol Sci. **34** —
  [DOI](https://www.sciencedirect.com/science/article/abs/pii/S0021850203000302)
- Pfeifer, S. et al. (2016), *Intercomparison of 15 aerodynamic particle size
  spectrometers (APS 3321)*, Atmos. Meas. Tech. **9**, 1545–1551 —
  [open access](https://amt.copernicus.org/articles/9/1545/2016/)
