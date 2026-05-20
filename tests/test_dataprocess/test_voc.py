"""Smoke tests for the AeroViz.voc top-level function."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from AeroViz.voc import voc_potentials


pytestmark = pytest.mark.dataprocess


SUPPORT_VOC = Path(__file__).resolve().parents[2] / (
    'AeroViz/dataProcess/VOC/support_voc.json'
)


@pytest.fixture(scope='module')
def supported_species():
    with SUPPORT_VOC.open() as fh:
        return list(json.load(fh).keys())


@pytest.fixture
def voc_df(supported_species):
    """Tiny VOC ppb dataframe with a handful of supported aromatic species."""
    # Pick 4 species we're sure exist
    picks = [s for s in ('Benzene', 'Toluene', 'Ethylbenzene', 'Ethane')
             if s in supported_species]
    assert picks, "support_voc.json missing expected species"
    n = 6
    rng = np.random.default_rng(0)
    return pd.DataFrame(
        {sp: rng.uniform(0.5, 5.0, n) for sp in picks},
        index=pd.date_range('2024-01-01', periods=n, freq='h'),
    )


def test_voc_potentials_returns_dict(voc_df):
    out = voc_potentials(voc_df)
    assert isinstance(out, dict)
    # Should have at least concentration / OFP / SOAP outputs
    assert any('OFP' in k or 'SOAP' in k or 'conc' in k.lower()
               for k in out.keys()), f"unexpected keys: {list(out.keys())}"


def test_voc_potentials_rejects_unknown_species(voc_df):
    bad = voc_df.assign(NotAVocSpecies=1.0)
    with pytest.raises((KeyError, ValueError)):
        voc_potentials(bad)
