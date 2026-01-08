"""
Deduplicate and analyze `data/game_distance_samples.csv`.

Produces:
- data/game_distance_samples_clean.csv (deduplicated rows)
- data/game_distance_fit.json (final fitted parameters + stats)

Fitting method: simple randomized hill-climb (no external deps).
"""

import os
import sys
import csv
import json
import math
# removed unused 'random' import
from statistics import mean  # not needed after simplification
import numpy as _np
from scipy.optimize import least_squares


# ensure repo root on sys.path
_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from core.constants import SCREEN_HEIGHT, SCREEN_WIDTH


DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
IN_PATH = os.path.join(DATA_DIR, "game_distance_samples.csv")
CLEAN_PATH = os.path.join(DATA_DIR, "game_distance_samples_clean.csv")
OUT_JSON = os.path.join(DATA_DIR, "game_distance_fit.json")


def read_samples(path):
    rows = []
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for r in reader:
            try:
                px = int(float(r.get("player_x", "")))
                py = int(float(r.get("player_y", "")))
                ex = int(float(r.get("enemy_x", "")))
                ey = int(float(r.get("enemy_y", "")))
                gd = r.get("game_distance", "").strip()
                if not gd:
                    continue
                gd = float(gd)
            except Exception:
                continue
            rows.append((px, py, ex, ey, gd))
    return rows


def dedupe_rows(rows):
    seen = set()
    out = []
    for (px, py, ex, ey, gd) in rows:
        key = (px, py, ex, ey)
        if key in seen:
            continue
        seen.add(key)
        out.append((px, py, ex, ey, gd))
    return out


def predict_units(params, px, py, tx, ty):
    # params: dict with keys unit_scale, v_top, v_bottom, k_sep, max_sep_mult
    unit_scale = params["unit_scale"]
    vertical_factor_top = params["v_top"]
    vertical_factor_bottom = params["v_bottom"]
    k_sep = params["k_sep"]
    max_sep_mult = params["max_sep_mult"]

    dx = float(px) - float(tx)
    dy = float(py) - float(ty)
    pixel_dist = math.hypot(dx, dy)
    if pixel_dist == 0:
        return 0.0

    norm_y = (float(py) - (SCREEN_HEIGHT / 2.0)) / (SCREEN_HEIGHT / 2.0)
    norm_y = max(-1.0, min(1.0, norm_y))
    t = (norm_y + 1.0) / 2.0
    v = vertical_factor_top * (1.0 - t) + vertical_factor_bottom * t

    # Note: no pos_min clamp (removed) — use pos_multiplier directly
    pos_multiplier = 1.0 + v

    sep_ratio = abs(dy) / pixel_dist
    sep_multiplier = 1.0 + (k_sep * sep_ratio)
    sep_multiplier = min(max_sep_mult, sep_multiplier)

    units = pixel_dist * unit_scale * pos_multiplier * sep_multiplier
    return float(units)


def loss_rmse(params, samples):
    errs = []
    for (px, py, ex, ey, gd) in samples:
        pred = predict_units(params, px, py, ex, ey)
        e = pred - gd
        errs.append(e * e)
    if not errs:
        return float("nan")
    return math.sqrt(sum(errs) / len(errs))


def fit_params(samples, seed=None, max_iters=5000):
    # Use SciPy's least_squares for a stronger optimizer.
    # Parameters: [unit_scale, v_top, v_bottom, k_sep, max_sep_mult]
    x0 = _np.array([
        1.142737888580297,  # unit_scale
        0.41,                # v_top
        -0.09,               # v_bottom
        0.3302259527161402,  # k_sep
        1.33,                # max_sep_mult
    ], dtype=float)

    lower = _np.array([0.1, -2.0, -2.0, 0.0, 1.0], dtype=float)
    upper = _np.array([5.0, 2.0, 2.0, 2.0, 5.0], dtype=float)

    Px = _np.array([s[0] for s in samples], dtype=float)
    Py = _np.array([s[1] for s in samples], dtype=float)
    Ex = _np.array([s[2] for s in samples], dtype=float)
    Ey = _np.array([s[3] for s in samples], dtype=float)
    Gd = _np.array([s[4] for s in samples], dtype=float)

    def residuals(x):
        params = {
            "unit_scale": float(x[0]),
            "v_top": float(x[1]),
            "v_bottom": float(x[2]),
            "k_sep": float(x[3]),
            "max_sep_mult": float(x[4]),
        }
        preds = _np.array([predict_units(params, px, py, ex, ey) for px, py, ex, ey in zip(Px, Py, Ex, Ey)])
        return preds - Gd

    res = least_squares(residuals, x0, bounds=(lower, upper), max_nfev=max_iters, method='trf')
    x_opt = res.x
    fitted = {
        "unit_scale": float(x_opt[0]),
        "v_top": float(x_opt[1]),
        "v_bottom": float(x_opt[2]),
        "k_sep": float(x_opt[3]),
        "max_sep_mult": float(x_opt[4]),
    }
    final_rmse = loss_rmse(fitted, samples)
    return fitted, final_rmse


def analyze(samples):
    # Fit on data
    fitted, rmse = fit_params(samples, seed=1, max_iters=8000)

    # compute additional stats: MAE and R^2
    preds = [predict_units(fitted, px, py, ex, ey) for (px, py, ex, ey, gd) in samples]
    actuals = [gd for (_, _, _, _, gd) in samples]
    n = len(actuals)
    if n == 0:
        raise ValueError("No samples")
    mae = sum(abs(p - a) for p, a in zip(preds, actuals)) / n
    mse = sum((p - a) ** 2 for p, a in zip(preds, actuals)) / n
    rmse = math.sqrt(mse)
    mean_actual = mean(actuals)
    ss_res = sum((a - p) ** 2 for p, a in zip(preds, actuals))
    ss_tot = sum((a - mean_actual) ** 2 for a in actuals)
    r2 = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else float("nan")

    return {
        "fitted_params": fitted,
        "rmse": rmse,
        "mae": mae,
        "r2": r2,
        "n": n,
    }


def compute_features(samples):
    # returns list of feature dicts and feature matrix + target
    feats = []
    X = []
    y = []
    for (px, py, ex, ey, gd) in samples:
        dx = ex - px
        dy = ey - py
        pixel_dist = math.hypot(dx, dy)
        log_dist = math.log1p(pixel_dist)
        norm_y = (py - (SCREEN_HEIGHT / 2.0)) / (SCREEN_HEIGHT / 2.0)
        signed_sep = 0.0 if pixel_dist == 0 else (dy / pixel_dist)
        sep_ratio = 0.0 if pixel_dist == 0 else (abs(dy) / pixel_dist)
        angle = math.atan2(dy, dx) if pixel_dist != 0 else 0.0
        angle_sin = math.sin(angle)
        angle_cos = math.cos(angle)
        abs_dx = abs(dx)
        abs_dy = abs(dy)
        rel_x = px / float(SCREEN_WIDTH)
        rel_y = py / float(SCREEN_HEIGHT)


def fit_ridge_linear(X, y, alpha=1e-3):
    # Add intercept column
    n, m = X.shape
    X0 = _np.hstack([_np.ones((n, 1)), X])
    I = _np.eye(m + 1)
    I[0, 0] = 0.0
    # closed-form ridge
    w = _np.linalg.solve(X0.T.dot(X0) + alpha * I, X0.T.dot(y))
    preds = X0.dot(w)
    residuals = preds - y
    mse = float(_np.mean(residuals ** 2))
    rmse = math.sqrt(mse)
    mae = float(_np.mean(_np.abs(residuals)))
    mean_y = float(_np.mean(y))
    ss_res = float(_np.sum((y - preds) ** 2))
    ss_tot = float(_np.sum((y - mean_y) ** 2))
    r2 = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else float('nan')
    return {
        "w": w.tolist(),
        "rmse": rmse,
        "mae": mae,
        "r2": r2,
        "preds": preds,
    }


def permutation_importance(w, X, y, feat_names):
    # w: full weight vector including intercept
    baseline_preds = _np.hstack([_np.ones((X.shape[0], 1)), X]).dot(_np.array(w))
    baseline_rmse = float(math.sqrt(_np.mean((baseline_preds - y) ** 2)))
    imps = []
    n = X.shape[0]
    rng = _np.random.RandomState(1)
    for j, name in enumerate(feat_names):
        Xp = X.copy()
        col = Xp[:, j].copy()
        perm = rng.permutation(n)
        col_shuffled = col[perm]
        Xp[:, j] = col_shuffled
        preds = _np.hstack([_np.ones((Xp.shape[0], 1)), Xp]).dot(_np.array(w))
        rmse = float(math.sqrt(_np.mean((preds - y) ** 2)))
        imps.append((name, baseline_rmse, rmse, rmse - baseline_rmse))
    imps_sorted = sorted(imps, key=lambda t: t[3], reverse=True)
    return imps_sorted


def cross_validate_feature_sets(samples, feat_names, X_full, y, k=5, seed=1, drop_names=None):
    if drop_names is None:
        drop_names = []
    n = len(samples)
    idx = _np.arange(n)
    rng = _np.random.RandomState(seed)
    rng.shuffle(idx)
    folds = _np.array_split(idx, k)

    metrics = {"ridge": [], "hybrid": []}

    for i in range(k):
        test_idx = folds[i]
        train_idx = _np.hstack([f for j, f in enumerate(folds) if j != i])

        # build train/test matrices
        X_train = X_full[train_idx]
        X_test = X_full[test_idx]
        y_train = y[train_idx]
        y_test = y[test_idx]

        # apply drop_names to get subset
        keep_names = [n for n in feat_names if n not in drop_names]
        keep_idxs = [feat_names.index(n) for n in keep_names]
        X_train_sub = X_train[:, keep_idxs]
        X_test_sub = X_test[:, keep_idxs]

        # parametric fit on train
        samples_train = [samples[j] for j in train_idx]
        fitted_train, _ = fit_params(samples_train, max_iters=4000)

        # param preds for train/test
        param_preds_train = _np.array([predict_units(fitted_train, px, py, ex, ey) for (px, py, ex, ey, _) in samples_train])
        samples_test = [samples[j] for j in test_idx]
        param_preds_test = _np.array([predict_units(fitted_train, px, py, ex, ey) for (px, py, ex, ey, _) in samples_test])

        # ridge on raw target
        ridge_tr = fit_ridge_linear(X_train_sub, y_train, alpha=1e-3)
        preds_lin_test = _np.hstack([_np.ones((X_test_sub.shape[0], 1)), X_test_sub]).dot(_np.array(ridge_tr["w"]))
        resid_lin = preds_lin_test - y_test
        rmse_lin = float(math.sqrt(_np.mean(resid_lin ** 2)))
        mae_lin = float(_np.mean(_np.abs(resid_lin)))
        mean_y = float(_np.mean(y_test)) if y_test.size else float('nan')
        ss_res = float(_np.sum((y_test - preds_lin_test) ** 2))
        ss_tot = float(_np.sum((y_test - mean_y) ** 2))
        r2_lin = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else float('nan')

        # ridge on residuals (hybrid)
        resid_target_train = y_train - param_preds_train
        ridge_resid_tr = fit_ridge_linear(X_train_sub, resid_target_train, alpha=1e-3)
        preds_resid_test = _np.hstack([_np.ones((X_test_sub.shape[0], 1)), X_test_sub]).dot(_np.array(ridge_resid_tr["w"]))
        preds_hybrid_test = param_preds_test + preds_resid_test
        resid_hybrid = preds_hybrid_test - y_test
        rmse_h = float(math.sqrt(_np.mean(resid_hybrid ** 2)))
        mae_h = float(_np.mean(_np.abs(resid_hybrid)))
        ss_res_h = float(_np.sum((y_test - preds_hybrid_test) ** 2))
        ss_tot_h = float(_np.sum((y_test - float(_np.mean(y_test))) ** 2))
        r2_h = 1.0 - (ss_res_h / ss_tot_h) if ss_tot_h > 0 else float('nan')

        metrics["ridge"].append({"rmse": rmse_lin, "mae": mae_lin, "r2": r2_lin})
        metrics["hybrid"].append({"rmse": rmse_h, "mae": mae_h, "r2": r2_h})

    # aggregate
    def agg(list_of_dicts):
        arr_rmse = _np.array([d["rmse"] for d in list_of_dicts], dtype=float)
        arr_mae = _np.array([d["mae"] for d in list_of_dicts], dtype=float)
        arr_r2 = _np.array([d["r2"] for d in list_of_dicts], dtype=float)
        return {"rmse_mean": float(_np.mean(arr_rmse)), "rmse_std": float(_np.std(arr_rmse)), "mae_mean": float(_np.mean(arr_mae)), "r2_mean": float(_np.mean(arr_r2))}

    return {"ridge": agg(metrics["ridge"]), "hybrid": agg(metrics["hybrid"])}


def write_clean(samples_clean, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["player_x", "player_y", "enemy_x", "enemy_y", "game_distance"])
        for (px, py, ex, ey, gd) in samples_clean:
            writer.writerow([px, py, ex, ey, gd])


def main():
    samples = read_samples(IN_PATH)
    print(f"Read {len(samples)} raw samples from {IN_PATH}")
    samples_clean = dedupe_rows(samples)
    print(f"After dedupe: {len(samples_clean)} samples")
    write_clean(samples_clean, CLEAN_PATH)
    print(f"Wrote deduped CSV: {CLEAN_PATH}")

    # Nonlinear parametric fit (existing model)
    result = analyze(samples_clean)
    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2)
    print(f"Wrote fit results: {OUT_JSON}")
    print("Parametric model summary:")
    print(json.dumps(result, indent=2))

    # Feature engineering and linear ridge regression
    feats, X, y = compute_features(samples_clean)
    ridge = fit_ridge_linear(X, y, alpha=1e-3)

    # parametric model predictions
    param_preds = _np.array([predict_units(result["fitted_params"], px, py, ex, ey) for (px, py, ex, ey, _) in samples_clean])

    # Fit ridge to predict residuals on top of parametric model (hybrid)
    residual_target = y - param_preds
    ridge_resid = fit_ridge_linear(X, residual_target, alpha=1e-3)
    hybrid_preds = param_preds + ridge_resid["preds"]

    # write augmented CSV with features, param-pred, linreg-pred, hybrid-pred, residuals
    aug_path = os.path.join(DATA_DIR, "game_distance_samples_features.csv")
    with open(aug_path, "w", newline="", encoding="utf-8") as fh:
        cols = ["player_x", "player_y", "enemy_x", "enemy_y", "game_distance"] + list(feats[0].keys()) + ["pred_param", "pred_lin_raw", "pred_hybrid", "residual_param", "residual_lin_raw", "residual_hybrid"]
        writer = csv.writer(fh)
        writer.writerow(cols)
        lin_preds = ridge["preds"]
        for (s, f, ppar, plin, phyb) in zip(samples_clean, feats, param_preds, lin_preds, hybrid_preds):
            px, py, ex, ey, gd = s
            row = [px, py, ex, ey, gd] + [f[k] for k in f.keys()] + [float(ppar), float(plin), float(phyb), float(ppar - gd), float(plin - gd), float(phyb - gd)]
            writer.writerow(row)
    print(f"Wrote augmented features CSV: {aug_path}")

    # report metrics
    mean_y = float(_np.mean(y))
    nrmse_lin = ridge["rmse"] / mean_y if mean_y != 0 else float('nan')
    print("Linear model (Ridge) metrics:")
    print(json.dumps({"rmse": ridge["rmse"], "mae": ridge["mae"], "r2": ridge["r2"], "nrmse": nrmse_lin}, indent=2))

    # hybrid metrics
    resid_hybrid = hybrid_preds - y
    rmse_hybrid = float(math.sqrt(_np.mean(resid_hybrid ** 2)))
    mae_hybrid = float(_np.mean(_np.abs(resid_hybrid)))
    ss_res_h = float(_np.sum((y - hybrid_preds) ** 2))
    ss_tot = float(_np.sum((y - float(_np.mean(y))) ** 2))
    r2_hybrid = 1.0 - (ss_res_h / ss_tot) if ss_tot > 0 else float('nan')
    nrmse_hybrid = rmse_hybrid / mean_y if mean_y != 0 else float('nan')
    print("Hybrid (parametric + ridge-on-residuals) metrics:")
    print(json.dumps({"rmse": rmse_hybrid, "mae": mae_hybrid, "r2": r2_hybrid, "nrmse": nrmse_hybrid}, indent=2))

    # feature coefficients (w includes intercept) for raw linear model
    feat_names = ["intercept"] + list(feats[0].keys())
    coeffs = dict(zip(feat_names, ridge["w"]))
    # coefficients for residual ridge
    coeffs_resid = dict(zip(feat_names, ridge_resid["w"]))
    # sort by absolute coeff magnitude
    sorted_feats = sorted(coeffs.items(), key=lambda kv: abs(kv[1]), reverse=True)
    print("Top feature coefficients (raw ridge):")
    for k, v in sorted_feats[:12]:
        print(f"  {k}: {v}")

    # --- Parametric ablation tests (3) ---
    print("\nParametric ablation tests:")

    # a) fix k_sep = 0 and refit remaining params
    def fit_params_fixed_ksep(samples, k_sep_fixed=0.0, max_iters=5000):
        x0 = _np.array([
            1.142737888580297,  # unit_scale
            0.41,                # v_top
            -0.09,               # v_bottom
            1.33,                # max_sep_mult
        ], dtype=float)
        lower = _np.array([0.1, -2.0, -2.0, 1.0], dtype=float)
        upper = _np.array([5.0, 2.0, 2.0, 5.0], dtype=float)

        Px = _np.array([s[0] for s in samples], dtype=float)
        Py = _np.array([s[1] for s in samples], dtype=float)
        Ex = _np.array([s[2] for s in samples], dtype=float)
        Ey = _np.array([s[3] for s in samples], dtype=float)
        Gd = _np.array([s[4] for s in samples], dtype=float)

        def residuals(x):
            params = {
                "unit_scale": float(x[0]),
                "v_top": float(x[1]),
                "v_bottom": float(x[2]),
                "k_sep": float(k_sep_fixed),
                "max_sep_mult": float(x[3]),
            }
            preds = _np.array([predict_units(params, px, py, ex, ey) for px, py, ex, ey in zip(Px, Py, Ex, Ey)])
            return preds - Gd

        res = least_squares(residuals, x0, bounds=(lower, upper), max_nfev=max_iters, method='trf')
        x_opt = res.x
        fitted = {
            "unit_scale": float(x_opt[0]),
            "v_top": float(x_opt[1]),
            "v_bottom": float(x_opt[2]),
            "k_sep": float(k_sep_fixed),
            "max_sep_mult": float(x_opt[3]),
        }
        final_rmse = loss_rmse(fitted, samples)
        return fitted, final_rmse

    fitted_noksep, rmse_noksep = fit_params_fixed_ksep(samples_clean, k_sep_fixed=0.0, max_iters=5000)
    print("Ablation k_sep=0 -> RMSE:", rmse_noksep)

    # b) remove vertical-varying term by enforcing v_top == v_bottom
    def fit_params_vfixed(samples, max_iters=5000):
        # params: [unit_scale, v (shared), k_sep, max_sep_mult]
        x0 = _np.array([
            1.142737888580297,  # unit_scale
            0.15,                # v (shared)
            0.3302259527161402,  # k_sep
            1.33,                # max_sep_mult
        ], dtype=float)
        lower = _np.array([0.1, -2.0, 0.0, 1.0], dtype=float)
        upper = _np.array([5.0, 2.0, 2.0, 5.0], dtype=float)

        Px = _np.array([s[0] for s in samples], dtype=float)
        Py = _np.array([s[1] for s in samples], dtype=float)
        Ex = _np.array([s[2] for s in samples], dtype=float)
        Ey = _np.array([s[3] for s in samples], dtype=float)
        Gd = _np.array([s[4] for s in samples], dtype=float)

        def residuals(x):
            params = {
                "unit_scale": float(x[0]),
                "v_top": float(x[1]),
                "v_bottom": float(x[1]),
                "k_sep": float(x[2]),
                "max_sep_mult": float(x[3]),
            }
            preds = _np.array([predict_units(params, px, py, ex, ey) for px, py, ex, ey in zip(Px, Py, Ex, Ey)])
            return preds - Gd

        res = least_squares(residuals, x0, bounds=(lower, upper), max_nfev=max_iters, method='trf')
        x_opt = res.x
        fitted = {
            "unit_scale": float(x_opt[0]),
            "v_top": float(x_opt[1]),
            "v_bottom": float(x_opt[1]),
            "k_sep": float(x_opt[2]),
            "max_sep_mult": float(x_opt[3]),
        }
        final_rmse = loss_rmse(fitted, samples)
        return fitted, final_rmse

    fitted_vfixed, rmse_vfixed = fit_params_vfixed(samples_clean, max_iters=5000)
    print("Ablation v_top==v_bottom -> RMSE:", rmse_vfixed)

    # --- Permutation importance (2) ---
    feat_names = list(feats[0].keys())
    per_imp = permutation_importance(ridge["w"], X, y, feat_names)
    print("\nPermutation importance (feature, base_rmse, perm_rmse, delta):")
    for name, base, perm, delta in per_imp:
        print(f"  {name}: base={base:.3f}, perm={perm:.3f}, delta={delta:.3f}")

    # Final reduced feature set applied (we keep `angle_cos`, removed `screen_center_dist`).
    print("Using final reduced feature set (keeps angle_cos; no screen_center_dist).")

    # save combined report
    combined = {
        "parametric": result,
        "linear_ridge": {"rmse": ridge["rmse"], "mae": ridge["mae"], "r2": ridge["r2"]},
        "ridge_on_residuals": {"rmse": ridge_resid["rmse"], "mae": ridge_resid["mae"], "r2": ridge_resid["r2"]},
        "hybrid": {"rmse": rmse_hybrid, "mae": mae_hybrid, "r2": r2_hybrid},
        "coefficients_raw_ridge": coeffs,
        "coefficients_resid_ridge": coeffs_resid,
    }
    with open(os.path.join(DATA_DIR, "game_distance_combined_report.json"), "w", encoding="utf-8") as fh:
        json.dump(combined, fh, indent=2)
    print("Wrote combined report: data/game_distance_combined_report.json")


if __name__ == "__main__":
    main()
