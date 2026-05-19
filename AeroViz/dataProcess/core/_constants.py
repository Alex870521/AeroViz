"""
Shared physical constants for AeroViz.dataProcess.

Single source of truth for values that are referenced across multiple
sub-modules (Optical, Chemistry, SizeDistr) so they cannot drift apart.
"""

# =============================================================================
# Refractive indices for common aerosol species
# =============================================================================
#
# Complex refractive index m = n + ki at two reference wavelengths in nm.
# Values follow the literature recommendations summarised below; if your
# study requires different values, override the relevant call site
# explicitly rather than editing this file.
#
# Provenance:
#   - AS / AN / SS         : Toon et al. (1976); k ≈ 0 in the visible
#   - OM (550 nm)          : Bond & Bergstrom (2006); slight k accounts for
#                            non-BC organic absorption typically present in
#                            atmospheric OA.
#   - OM (450 nm)          : Kirchstetter et al. (2004); BrC absorbs more
#                            strongly toward the UV.
#   - Soil / dust          : Levoni et al. (1997); small k from iron oxides.
#   - EC                   : Bond & Bergstrom (2006). The older value of
#                            0.54 (Hess et al. 1998) underestimates BC
#                            absorption; 0.72 is the modern compromise that
#                            accounts for "atmospheric" BC including light
#                            absorption by coatings.
#   - ALWC (liquid water)  : standard pure water RI.
#
REFRACTIVE_INDEX = {
    '550': {
        'ALWC': 1.333 + 0j,
        'AS':   1.53 + 0j,
        'AN':   1.55 + 0j,
        'OM':   1.55 + 0.0163j,
        'Soil': 1.56 + 0.006j,
        'SS':   1.54 + 0j,
        'EC':   1.80 + 0.72j,
    },
    '450': {
        'ALWC': 1.333 + 0j,
        'AS':   1.57 + 0j,
        'AN':   1.57 + 0j,
        'OM':   1.58 + 0.056j,
        'Soil': 1.56 + 0.009j,
        'SS':   1.54 + 0j,
        'EC':   1.80 + 0.79j,
    },
}
