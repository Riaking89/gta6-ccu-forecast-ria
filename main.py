"""GTA VI Twitch CCU forecaster — make.fun gta6-twitch-ccu-forecast-01.

Forecasts, for each of hours 2..24 of GTA VI's release day (2026-11-19 UTC),
five quantiles of Twitch's concurrent viewers in the "Grand Theft Auto VI"
category, from the case's hour-1 print plus the comparable past launches it
carries. Python 3.13, standard library only, no network, deterministic.

Method (found by studying the 38 comparable launches in the practice cases):
a launch's release-day curve, measured as log(viewers_h / viewers_1), is
almost entirely explained by its hour-1 level. Across comparables the
correlation between log(hour-1 viewers) and log(peak / hour-1) is about
-0.94 with slope about -0.93: the day's late peak sits near a fixed
absolute level (prime-time Twitch audience for a big launch), while hour 1
varies wildly with pre-launch buzz. So for each hour h we fit, over the
comparable launches, an ordinary-least-squares line of log-ratio on
log(hour-1 viewers) and take the fitted value at this case's hour-1 print
as the median log-ratio.

The spread blends two honest estimates of the same uncertainty, averaged
in log space: a normal spread from the per-hour residual interquartile
range, and the empirical quantiles of all residuals pooled across hours.
Blending keeps the outer quantiles from trusting either the normal shape
or the noisy 37-point per-hour tails alone.

On the four practice cases (answers read from SullyGnome's public hourly
averages, the same source the kit's NOTICE.txt documents) this scores a
mean pinball loss of about 0.223, against the house persistence baseline's
0.387 — roughly 42% better, and it beats the baseline on every case.

Fallback: with fewer than 5 usable comparable curves the program falls
back to the house persistence shape (flat median, widening spread), so it
still writes a valid forecast.
"""

import json
import math
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# The grader's -P leaves /bot off sys.path: put it back first, so a helper
# module shipped beside this file would import. (This entry is one file.)
sys.path.insert(0, str(Path(__file__).resolve().parent))

INPUT_DIR = Path(os.environ.get("MAKEFUN_INPUT_DIR", "/input"))
OUTPUT_DIR = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))

# The quantile levels the contest scores, in the order each row lists them.
LEVELS = [0.05, 0.25, 0.5, 0.75, 0.95]
# At least this many comparable release-day curves, or fall back.
MIN_CURVES = 5
# Blend weight: half normal-spread forecast, half pooled-residual forecast.
BLEND_W = 0.5
# Floor on the per-hour log-spread, so a lucky tight hour never goes razor thin.
SIGMA_FLOOR = 0.15


def norm_ppf(p: float) -> float:
    """Inverse standard-normal CDF (Acklam's rational approximation)."""
    if not 0.0 < p < 1.0:
        raise ValueError(f"level {p} outside (0, 1)")
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    plow = 0.02425
    phigh = 1 - plow
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
            ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    if p > phigh:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
            ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    q = p - 0.5
    r = q * q
    return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / \
        (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)


def round2(x: float) -> float | int:
    """x rounded to 2 decimals, half up (as the starter rounds it)."""
    scaled = x * 100
    whole = math.floor(scaled)
    if scaled - whole >= 0.5:
        whole += 1
    value = whole / 100
    return int(value) if value.is_integer() else value


def parse_ts(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ")


def release_day_curve(comp: dict) -> list[float] | None:
    """A comparable's 24 hourly viewer counts on its release day, or None.

    Needs all 24 UTC hours of day_start present with positive counts; the
    GTA VI category itself (data only to 2026-11-17, before its release) and
    any sparse small category fail this and are left out.
    """
    day_start = parse_ts(comp["day_start"])
    by_hour: dict[int, float] = {}
    for point in comp["hourly"]:
        t = parse_ts(point["from"])
        if day_start <= t < day_start + timedelta(days=1):
            by_hour[t.hour + 1] = point["viewers"]
    if len(by_hour) < 24:
        return None
    series = [by_hour[h] for h in range(1, 25)]
    if any(v <= 0 for v in series):
        return None
    return series


def ols(xs: list[float], ys: list[float]) -> tuple[float, float]:
    """Least-squares line y = a + b*x; returns (a, b)."""
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    denom = sum((x - mx) ** 2 for x in xs)
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / denom if denom else 0.0
    return my - b * mx, b


def quantile(sorted_vals: list[float], tau: float) -> float:
    """Linear-interpolation quantile of an already sorted list."""
    n = len(sorted_vals)
    pos = tau * (n - 1)
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return sorted_vals[lo]
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (pos - lo)


def persistence_row(p1: float, h: int, levels: list[float]) -> list[float | int]:
    """House persistence shape: flat median, spread widening like sqrt(h-1)."""
    return [round2(max(1.0, min(1e9, p1 * math.exp(norm_ppf(tau) * 0.15 * math.sqrt(h - 1)))))
            for tau in levels]


def forecast_case(case: dict) -> dict:
    levels = list(case.get("levels") or LEVELS)
    zs = [norm_ppf(tau) for tau in levels]
    known = next((k for k in case["known"] if k["hour"] == 1), None)
    p1 = max(1.0, float(known["viewers"])) if known else 1.0

    curves = []
    for comp in case.get("comparables") or []:
        series = release_day_curve(comp)
        if series is not None:
            curves.append(series)

    hours = [row["hour"] for row in case["forecast"]]
    if len(curves) < MIN_CURVES:
        return {"hours": [{"hour": h, "q": persistence_row(p1, h, levels)} for h in hours]}

    log_p1 = math.log(p1)
    # Per hour: OLS of log-ratio on log(hour-1), residuals pooled across hours.
    # Fits are built only for the hours this case actually asks for.
    fits: dict[int, tuple[float, float]] = {}
    pooled: list[float] = []
    for h in hours:
        if h < 2 or h > 24:
            continue
        xs = [math.log(s[0]) for s in curves]
        ys = [math.log(s[h - 1] / s[0]) for s in curves]
        a, b = ols(xs, ys)
        residuals = sorted(y - (a + b * x) for x, y in zip(xs, ys))
        iqr = quantile(residuals, 0.75) - quantile(residuals, 0.25)
        sigma = max(SIGMA_FLOOR, iqr / 1.349)
        fits[h] = (a + b * log_p1, sigma)
        pooled.extend(residuals)
    pooled.sort()

    rows = []
    for h in hours:
        median, sigma = fits[h]
        row = []
        for tau, z in zip(levels, zs):
            log_normal = median + z * sigma
            log_pooled = median + quantile(pooled, tau)
            value = p1 * math.exp((1 - BLEND_W) * log_normal + BLEND_W * log_pooled)
            row.append(round2(max(1.0, min(1e9, value))))
        # Rounding is monotone, but enforce non-decreasing as a belt-and-braces.
        for i in range(1, len(row)):
            if row[i] < row[i - 1]:
                row[i] = row[i - 1]
        rows.append({"hour": h, "q": row})
    return {"hours": rows}


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    # Every case file, in name order, so two runs write the same bytes.
    for path in sorted(INPUT_DIR.glob("*.in")):
        case = json.loads(path.read_text(encoding="utf-8"))
        forecast = forecast_case(case)
        (OUTPUT_DIR / f"{path.stem}.out").write_text(
            json.dumps(forecast, separators=(",", ":")) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
