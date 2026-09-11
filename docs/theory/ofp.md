# Ozone Formation Potential (OFP)

Ozone Formation Potential (OFP) evaluates the contribution of volatile organic compounds (VOCs) to tropospheric ozone formation.

## Basic Principles

VOCs react with NOx under sunlight to form ozone:

$$VOC + NO_x + h\nu \rightarrow O_3 + \text{products}$$

Different VOCs have vastly different reactivities, so quantifying the relative contribution of each species is necessary.

## Maximum Incremental Reactivity (MIR)

### Definition

MIR (Maximum Incremental Reactivity) represents the amount of ozone produced per unit mass of VOC under optimal conditions:

$$MIR_i = \frac{\partial [O_3]}{\partial [VOC_i]}_{max}$$

Units: g O3 / g VOC

### Typical MIR Values

| VOC Species | MIR (g O3/g VOC) | Reactivity Class |
|-------------|------------------|------------------|
| Methane | 0.014 | Very low |
| Ethane | 0.28 | Low |
| Propane | 0.49 | Low |
| Ethylene | 9.00 | High |
| Propylene | 11.66 | High |
| Toluene | 4.00 | Medium |
| Xylene | 7.80 | High |
| Formaldehyde | 9.46 | High |
| Isoprene | 10.61 | High |

## OFP Calculation

### Single Species

$$OFP_i = C_i \times MIR_i$$

Where:
- $C_i$ = Concentration of species i (ug/m3)
- $MIR_i$ = MIR value of species i

### Total OFP

$$OFP_{total} = \sum_i C_i \times MIR_i$$

## Secondary Organic Aerosol Potential (SOAP)

### Definition

SOAP (Secondary Organic Aerosol Potential) evaluates the ability of VOCs to form secondary organic aerosol:

$$SOAP_i = C_i \times SOAP_{factor,i}$$

### Typical SOAP Factors

| VOC Species | SOAP Factor | Description |
|-------------|-------------|-------------|
| Benzene | 1.0 | Reference species |
| Toluene | 2.7 | Moderate SOA formation |
| Xylene | 5.5 | High SOA formation |
| alpha-Pinene | 32 | Very high (biogenic) |
| Isoprene | 2.4 | Biogenic |

## VOC Reactivity Classification

### By Chemical Category

| Category | Typical Reactivity | Representative Species |
|----------|-------------------|----------------------|
| Alkanes | Low-Medium | Ethane, Propane, Butane |
| Alkenes | High | Ethylene, Propylene, Butene |
| Aromatics | Medium-High | Benzene, Toluene, Xylene |
| Aldehydes | High | Formaldehyde, Acetaldehyde |
| Terpenes | Very High | Isoprene, alpha-Pinene |

## In AeroViz

Usage lives in the guide: [VOC Analysis](../guide/voc_analysis.md) for reading the file with pandas and calling `voc_potentials`; the supported species and their MIR / SOAP factors are on the [VOC data page](../api/instruments/chemical/VOC.md).

## Applications

1. **Source Identification**: Different sources have distinct VOC compositions and OFP characteristics
2. **Control Strategies**: Prioritize controlling high-reactivity VOCs
3. **Ozone Prediction**: Estimate the impact of VOC emission reductions on ozone levels

## References

1. Carter, W. P. L. (2010). Development of the SAPRC-07 chemical mechanism. *Atmos. Environ.*, 44(40), 5324-5335.
2. Derwent, R. G., et al. (2010). Photochemical ozone creation potentials (POCPs) for different emission sources of organic compounds under European conditions estimated with a Master Chemical Mechanism. *Atmos. Environ.*, 41(12), 2570-2579.
