"""Automated H0 / H1 evaluation.

The proposal's alternative hypothesis (H1) is supported when:
    a) larger fuel shocks produce monotonically higher COL and lower
       buying power (dose-response),
    b) low-income and transport-dependent households are hit harder
       than higher-income households,
    c) stronger government responses noticeably reduce the negative
       effects for vulnerable groups compared with no response.

This module checks each criterion against the scenario summary CSV and
returns a dict + markdown verdict suitable for slides.
"""

from __future__ import annotations

from pathlib import Path

import json
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RUNS_DIR = ROOT / "output" / "runs"
PROJ_DIR = ROOT / "output" / "projections"


def _monotonic_increasing(values: list[float]) -> bool:
    return all(b >= a - 1e-6 for a, b in zip(values, values[1:]))


def _monotonic_decreasing(values: list[float]) -> bool:
    return all(b <= a + 1e-6 for a, b in zip(values, values[1:]))


DOSE_RESPONSE_SCENARIOS = ["S0_baseline", "S1_small_shock", "S2_pids_current", "S3_severe_shock"]


def evaluate() -> dict:
    summary = pd.read_csv(RUNS_DIR / "summary.csv")
    indexed = summary.set_index("scenario")
    dose = indexed.loc[DOSE_RESPONSE_SCENARIOS]

    col_values = dose["col_index"].tolist()
    bp_values = dose["mean_buying_power"].tolist()
    low_counts = dose["count_low"].tolist()

    h1_dose_response = (
        _monotonic_increasing(col_values)
        and _monotonic_decreasing(bp_values)
        and _monotonic_increasing(low_counts)
    )

    s2 = summary[summary["scenario"] == "S2_pids_current"].iloc[0]
    s5 = summary[summary["scenario"] == "S5_pids_current_gov2"].iloc[0]
    h1_policy_mitigation = (
        s5["mean_buying_power"] > s2["mean_buying_power"]
        and s5["count_low"] <= s2["count_low"]
        and s5["col_index"] <= s2["col_index"]
    )

    severe = summary[summary["scenario"] == "S3_severe_shock"].iloc[0]
    baseline = summary[summary["scenario"] == "S0_baseline"].iloc[0]
    low_loss_pct = (severe["buying_power_low"] - baseline["buying_power_low"]) / max(baseline["buying_power_low"], 1) * 100
    high_loss_pct = (severe["buying_power_high"] - baseline["buying_power_high"]) / max(baseline["buying_power_high"], 1) * 100
    h1_distributional = low_loss_pct < high_loss_pct

    verdict = {
        "h1_dose_response": bool(h1_dose_response),
        "h1_policy_mitigation": bool(h1_policy_mitigation),
        "h1_distributional": bool(h1_distributional),
        "supports_h1": bool(h1_dose_response and h1_policy_mitigation and h1_distributional),
        "details": {
            "col_index_no_policy_path": col_values,
            "mean_buying_power_no_policy_path": bp_values,
            "low_class_no_policy_path": low_counts,
            "low_income_loss_pct_severe": float(low_loss_pct),
            "high_income_loss_pct_severe": float(high_loss_pct),
            "policy_mitigation_buying_power_delta": float(s5["mean_buying_power"] - s2["mean_buying_power"]),
            "policy_mitigation_low_delta": int(s5["count_low"] - s2["count_low"]),
        },
    }
    return verdict


def write_outputs(verdict: dict) -> None:
    PROJ_DIR.mkdir(parents=True, exist_ok=True)
    with (PROJ_DIR / "hypothesis_verdict.json").open("w", encoding="utf-8") as fh:
        json.dump(verdict, fh, indent=2)


def as_markdown(verdict: dict) -> str:
    yes = "Supported"
    no = "Not supported"

    lines: list[str] = []
    lines.append("# Hypothesis evaluation\n")
    lines.append(f"**Overall verdict:** {'**H1 supported**' if verdict['supports_h1'] else '**H0 retained**'}\n")
    lines.append("| Criterion | Result |")
    lines.append("|-----------|--------|")
    lines.append(f"| Dose-response (higher shock -> higher COL, lower buying power, more low-class) | "
                 f"{yes if verdict['h1_dose_response'] else no} |")
    lines.append(f"| Policy mitigation (gov=2 vs gov=0 at +40% shock) | "
                 f"{yes if verdict['h1_policy_mitigation'] else no} |")
    lines.append(f"| Distributional impact (low-income loses more than high-income) | "
                 f"{yes if verdict['h1_distributional'] else no} |")
    lines.append("")
    d = verdict["details"]
    lines.append("## Supporting numbers\n")
    lines.append(f"- COL index (no-policy) across shock levels: {d['col_index_no_policy_path']}")
    lines.append(f"- Mean buying power (no-policy): {d['mean_buying_power_no_policy_path']}")
    lines.append(f"- Low-class count (no-policy): {d['low_class_no_policy_path']}")
    lines.append(f"- Severe-shock real loss: low-income {d['low_income_loss_pct_severe']:.2f}% vs "
                 f"high-income {d['high_income_loss_pct_severe']:.2f}%")
    lines.append(f"- Gov=2 buying-power boost vs gov=0 at +40% shock: "
                 f"PHP {d['policy_mitigation_buying_power_delta']:,.0f}; "
                 f"low-class delta: {d['policy_mitigation_low_delta']}")
    return "\n".join(lines)


def main() -> None:
    verdict = evaluate()
    write_outputs(verdict)
    print(as_markdown(verdict))


if __name__ == "__main__":
    main()
