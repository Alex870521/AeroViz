"""Smoke tests for the public AeroViz import surface.

Marked ``dataprocess`` because they exercise the post-processing
namespaces (no reader I/O). Keep cheap — these are intentionally minimal
import-only checks; any heavy compute belongs in
``tests/test_dataprocess/``.
"""
import pytest


pytestmark = pytest.mark.dataprocess


def test_root_package():
    import AeroViz  # noqa: F401


def test_io_and_tools():
    from AeroViz import RawDataReader, DataBase, DataClassifier, plot  # noqa: F401


def test_legacy_dataprocess():
    from AeroViz import DataProcess  # noqa: F401


def test_subnamespaces():
    from AeroViz import chemistry, optical, size, voc  # noqa: F401


def test_chemistry_flat_aliases():
    from AeroViz import (  # noqa: F401
        reconstruct_mass,
        split_oc_ec,
        partition_ratios,
        isoropia,
        volume_ri,
        kappa,
        growth_factor,
    )


def test_optical_flat_aliases():
    from AeroViz import (  # noqa: F401
        optical_basic,
        mie,
        improve,
        gas_extinction,
        retrieve_ri,
        brown_carbon,
        mie_lognormal,
        mie_multimodal,
        scattering_function,
        scattering_function_sd,
        phase_matrix,
        nephelometer_truncation_correction,
        mie_core_shell,
        mie_core_shell_sd,
        iterative_inversion,
        iterative_inversion_sd,
        contour_intersection,
    )


def test_size_flat_aliases():
    from AeroViz import psd_stats, psd_distributions, merge_psd  # noqa: F401


def test_voc_flat_aliases():
    from AeroViz import voc_potentials  # noqa: F401
