import json
from pathlib import Path

import numpy as np
import pytest

from reon_model import AgingConfig, draw_cell_parameters
from reon_model.calibration import beta_life, fit_hinges

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "paper" / "repo"
CALIB = ROOT / "data" / "calibration_zhou2026.json"


def test_fit_hinges_recovers_synthetic_cells():
    rng = np.random.default_rng(0)
    km = np.linspace(75, 300, 2000)
    n = 30
    a, e = rng.normal(0.94, 0.005, n), rng.uniform(5e-5, 2e-4, n)
    s, tau = rng.uniform(4e-4, 1.4e-3, n), rng.uniform(210, 260, n)
    Q = a - e * (km[:, None] - km[0]) - s * np.maximum(km[:, None] - tau, 0) + rng.normal(0, 2e-4, (km.size, n))
    h = fit_hinges(km, Q)
    np.testing.assert_allclose(h.tau, tau, atol=2.0)
    np.testing.assert_allclose(h.s, s, rtol=0.05)
    np.testing.assert_allclose(h.e, e, rtol=0.1, atol=5e-6)


def test_draw_cell_parameters_moments():
    ag = AgingConfig(kappa_spread_scale=1.0)
    d = draw_cell_parameters(ag, 200_000, np.random.default_rng(1))
    z = np.column_stack([d["m"], d["tau_rel"], d["kappa"] / ag.knee_slope_ratio])
    np.testing.assert_allclose(z.mean(axis=0), 1.0, atol=0.01)
    np.testing.assert_allclose(np.cov(z, rowvar=False), np.array(ag.cell_cov), atol=0.006)
    # temperature carries the Arrhenius share of the aging multiplier
    slope = np.polyfit(d["temp"], d["m"], 1)[0]
    assert slope == pytest.approx(ag.arrhenius_slope, rel=0.1)


def test_conditioning_on_slot_temperature_keeps_marginals():
    ag = AgingConfig()
    rng = np.random.default_rng(2)
    temp = ag.temp_sd_C * rng.standard_normal(200_000)
    d = draw_cell_parameters(ag, temp.size, rng, temp=temp)
    assert d["m"].std() == pytest.approx(np.sqrt(ag.cell_cov[0][0]), rel=0.03)


def test_beta_life_identical_cells_is_one():
    km = np.linspace(0, 400, 401)
    Q = np.tile(1.0 - 0.0005 * km, (1, 10, 1))
    assert beta_life(km, Q)[0] == pytest.approx(1.0)


@pytest.mark.skipif(not DATA.exists(), reason="run scripts/fetch_paper_data.sh")
def test_calibration_reproduces_committed_parameters():
    from reon_model.calibration import calibrate
    c = calibrate(DATA)
    saved = json.loads(CALIB.read_text())["aging"]
    for k in ("knee_slope_ratio", "q0_cv", "knee_onset_fade", "knee_pack_logsd", "resistance_growth"):
        assert c["aging"][k] == pytest.approx(saved[k], rel=1e-3)
    np.testing.assert_allclose(c["aging"]["cell_cov"], saved["cell_cov"], atol=1e-4)


@pytest.mark.skipif(not DATA.exists(), reason="run scripts/fetch_paper_data.sh")
def test_calibrated_model_matches_held_out_fig5_before_300k_km():
    from reon_model.calibration import validate
    c = json.loads(CALIB.read_text())
    v = validate(c, DATA, n_packs=300, seed=3)
    for r in v["fig5_by_mileage"]:
        if r["km_bin"] in ("50-100k", "100-150k", "150-200k"):
            assert r["model_mean"] == pytest.approx(r["data_mean"], rel=0.15 if r["metric"] == "sigma_soh" else 0.01)
    assert v["fig5c_beta_life"]["model_mean"] == pytest.approx(v["fig5c_beta_life"]["data_mean"], abs=0.02)
