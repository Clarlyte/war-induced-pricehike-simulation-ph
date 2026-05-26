# Presentation Guide — Philippine Fuel-Shock ABM

A 7-minute demo plan covering all four rubric criteria, with a script,
backup figures, and anticipated Q&A.

## Suggested slide order (10 slides)

| # | Slide | Talking point | Source on disk |
|---|-------|---------------|----------------|
| 1 | Title + research question | "How does a war-driven oil shock change household buying power in the Philippines, and how unevenly does it hit different families?" | Proposal Section 1 |
| 2 | Problem statement | Importation dependence, near-poor vulnerability, regressive welfare loss | Proposal Section 2 + PIDS 2026 numbers |
| 3 | Hypotheses | H0 = no meaningful impact; H1 = significant + regressive impact mitigated by targeted policy | Proposal Section 3 |
| 4 | Model definition | Agents = households with FIES-calibrated attributes; environment = oil shock + pass-through + policy; outcomes = food/utilities/transport spend, buying power, COL index | README Components 2–7 |
| 5 | Live dashboard demo | Move sliders during the talk — see Demo script below | `solara run pricehike_abm/app.py` |
| 6 | Scenario matrix | 8 scenarios; show summary table | `output/runs/summary.csv` |
| 7 | Dose-response curve | "Bigger shock = higher COL and lower buying power, monotonically." | `output/figures/shock_response_curve.png` |
| 8 | Distributional impact | "Low-income households lose ~2x as much real buying power as high-income at +60% shock." | `output/figures/buying_power_by_class.png` |
| 9 | Policy effect | "Targeted level-2 response restores buying power to near-baseline and prevents class downgrades." | `output/figures/policy_effect.png` |
| 10 | Hypothesis verdict + limitations + Q&A | Read the H1 verdict; flag partial-equilibrium and synthetic-agent caveats | `output/projections/hypothesis_verdict.json`, README limitations |

## Live demo script (5 minutes)

1. **Open the dashboard.** `solara run pricehike_abm/app.py` → http://127.0.0.1:8765/.
2. **Baseline.** Oil shock = 0. Press Step a few times. "Every house is green or orange; COL stays at 100; no households in the low class." Point at the world view and monitors.
3. **Apply a war shock.** Slide oil shock to **+40%**. Press Step. "Watch the orange houses creep towards red, especially in the rural ring. The COL index rises above 100 and the low-class counter ticks up."
4. **Push to severe.** Slide oil shock to **+60%**. Step a couple more times. "Now we see ~30 households slip into the red zone — these are the near-poor in PIDS' policy note."
5. **Apply government response.** Switch the dropdown to **Level 2**. Step once. "Targeted transfers and a 40% fuel subsidy lift most families back; the red houses fade to orange or green within a month."
6. **Stress the system.** Push fuel pass-through up, drop policy back to 0. "This is what happens if the government does nothing and oil firms pass everything through to the pump."
7. **Reset and pivot to slides.** Press Reset → switch to slide 6 (scenario matrix).

## If the live demo fails

Have the static figures ready in `output/figures/` (already exported by
`python -m analysis.generate_report`):

- `shock_response_curve.png`
- `col_by_scenario.png`
- `buying_power_by_class.png`
- `rural_urban_gap.png`
- `policy_effect.png`
- `class_migration_S0_baseline.png` / `_S2_pids_current.png` / `_S3_severe_shock.png` / `_S5_pids_current_gov2.png`

## Anticipated Q&A

**Q: Why Python and not NetLogo?**
A: We needed a build with reproducible CSV outputs and a live web
dashboard. Mesa is the standard Python ABM library; Solara gives us a
NetLogo-style interface in the browser without packaging headaches. The
underlying model logic (agents, environment, pass-through rules) is the
same as a NetLogo implementation would be.

**Q: How does this connect to real PIDS numbers?**
A: PIDS' 2026 policy note projects an additional 1.34M Filipinos pushed
into poverty under a 35% pass-through at $105/bbl, with rural poverty
rising 1.5pp vs 0.9pp urban. We use the same 35% baseline pass-through,
the same urban/rural asymmetry, and the same general targeting
recommendation. Our model is qualitative — we don't claim to replicate
the 1.34M number, only the directional and distributional patterns.

**Q: Why are food-at-risk percentages near zero in the report?**
A: Households first draw down savings and trim the "other" budget before
cutting food. In our 12-month run with synthetic savings buffers, very
few agents fully exhaust their buffer. To trigger more food stress you
can either drop the savings shares in `parameters.yaml` or run the +80%
shock scenario.

**Q: Is the rural population sample representative?**
A: We target 55% rural / 45% urban from the 2020 PSA Census. The 150
agents are a deterministic sample (seed = 42); see
`data/household_profiles.csv`. Mean attribute shares are within ±5pp of
target.

**Q: How is "buying power" defined?**
A: Following proposal Section 4.1: `buying power = effective_income −
(food + utilities + transport)`. This is residual cash for everything
non-essential. The `buying_power_ratio` we use for class migration is
this residual divided by effective income.

**Q: Why does gov level 2 sometimes look "too good" (buying power above baseline)?**
A: Targeted income transfers add cash on top of incomes when shocks are
on. We deliberately let level 2 over-correct so the audience can see how
much room there is between "no response" and "strong response." A
realistic calibration would tax-finance the transfers, which we don't
model (see limitations).

**Q: Reproducibility?**
A: Seed = 42 (in `parameters.yaml` and propagated through the Mesa
Model). Reinstall, re-run, identical numbers.

## Rubric checklist

- [x] Clearly defined agents, behaviors, and interactions documented in
  README Component 2 and codebase.
- [x] Sophisticated justifications: every coefficient is YAML-bound with a
  `source` and `note`.
- [x] Simulation runs smoothly; live dashboard with controls + speed +
  reset; emergent class migration visible.
- [x] Analysis with visuals: nine figures, projections, inequality
  metrics, automated H1 verdict.
- [x] Critical discussion: implications and limitations sections in both
  README and `output/analysis_report.md`.
- [x] Communication aids: this guide + demo script + backup figures.
