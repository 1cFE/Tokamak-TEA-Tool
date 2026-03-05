"""
fusion_buildings_cost.py
========================
Account 21: Structures & Site Facilities for a D-T tokamak FPP.

Replicates Araiinejad (2024/2025) methodology:
  1. EEDB PWR12 Better-Experience baseline building costs
  2. NCET power-law scaling to fusion plant electric output
  3. Reactor building volume adjustment for compact HTS tokamak
     (ITER Tokamak Hall scaled by torus volume ratio)
  4. Regulatory sensitivity: divide nuclear building costs by 2.2×
     for the lower bound (fusion ≠ fission safety case)

Calibrated to reproduce Table 17 values:
  ARAI (350 MWe, R0=3.3m, a=1.13m):
    Lower bound:  819 $/kW  ✓
    Upper bound: 1317 $/kW  ✓

Usage:
    from fusion_buildings_cost import structures_cost
    
    result = structures_cost(
        P_e_net=350,      # MWe net electric
        R0=3.3,           # m, major radius
        a=1.13,           # m, minor radius
        kappa=1.84,       # elongation
        regulatory='lower'
    )
    print(result)
    print(f"Structures cost: {result.total_structures_per_kW:.0f} $/kW")
"""

import math
from dataclasses import dataclass
from typing import Optional


# ═══════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════

PWR12_PE   = 1200.0   # MWe, EEDB reference plant
N_SCALE    = 0.6      # NCET power-law exponent
REG_FACTOR = 2.2      # Stewart & Shirvan (2022) nuclear safety multiplier

# ITER reference geometry (volume ratio baseline)
ITER_R0    = 6.2      # m
ITER_A     = 2.0      # m
ITER_KAPPA = 1.7


# ═══════════════════════════════════════════════════════════════════════
# CALIBRATED BASELINE
#
# PWR12-BE building costs at 1200 MWe in 2021$M, reverse-engineered
# from Araiinejad Table 17 endpoints (819 / 1317 $/kW at 350 MWe).
#
# The two known values plus the regulatory factor (2.2) uniquely
# determine the nuclear/conventional split:
#
#   Upper: N + C = 1317 × 350 / 1000 = 461.0 $M
#   Lower: N/2.2 + C = 819 × 350 / 1000 = 286.7 $M
#   Solve: N = 319.6 $M at 350 MWe, C = 141.4 $M at 350 MWe
#
# De-scaling to 1200 MWe reference (via power and volume factors)
# gives the baseline values below.
#
# Reactor building fraction (0.65) is consistent with PWR12-BE
# containment being ~65% of nuclear building costs.
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class BuildingBaseline:
    """
    PWR12-BE baseline building costs at 1200 MWe (2021$M).
    
    Override these if you want to recalibrate to different EEDB 
    data or different known cost endpoints.
    """
    nuclear_total: float = 1143.0        # $M at 1200 MWe
    reactor_bldg_fraction: float = 0.65  # fraction subject to volume scaling
    conventional_total: float = 296.0    # $M at 1200 MWe


DEFAULT_BASELINE = BuildingBaseline()


# ═══════════════════════════════════════════════════════════════════════
# OUTPUT CONTAINER
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class StructuresCostResult:
    """Account 21 cost estimate output."""
    # Costs ($M)
    nuclear_buildings_M:      float
    conventional_buildings_M: float
    total_structures_M:       float

    # Per-kW metric
    total_structures_per_kW:  float

    # Diagnostics
    power_scale_factor:       float   # (P_e / 1200)^0.6
    volume_ratio:             float   # V_fusion / V_ITER (torus proxy)
    reactor_bldg_vol_factor:  float   # volume_ratio^0.6
    regulatory_divisor:       float   # 2.2 (lower) or 1.0 (upper)

    def __repr__(self):
        return (
            f"Account 21: Structures & Site Facilities\n"
            f"  Nuclear buildings:      ${self.nuclear_buildings_M:>8,.0f} M\n"
            f"  Conventional buildings: ${self.conventional_buildings_M:>8,.0f} M\n"
            f"  TOTAL:                  ${self.total_structures_M:>8,.0f} M  "
            f"({self.total_structures_per_kW:,.0f} $/kW)\n"
            f"  ──────────────────────────────────────\n"
            f"  Power scale (P_e/1200)^0.6:  {self.power_scale_factor:.4f}\n"
            f"  Volume ratio (vs ITER):      {self.volume_ratio:.4f}\n"
            f"  Reactor bldg vol factor:     {self.reactor_bldg_vol_factor:.4f}\n"
            f"  Regulatory divisor:          {self.regulatory_divisor:.1f}"
        )


# ═══════════════════════════════════════════════════════════════════════
# CORE FUNCTION
# ═══════════════════════════════════════════════════════════════════════

def structures_cost(
    P_e_net: float,
    R0: float,
    a: float,
    kappa: float = 1.84,
    regulatory: str = 'lower',
    baseline: Optional[BuildingBaseline] = None,
) -> StructuresCostResult:
    """
    Compute Account 21: Structures & Site Facilities cost.

    Parameters
    ----------
    P_e_net : float
        Net electric power [MWe].
    R0 : float
        Major radius [m].
    a : float
        Minor radius [m].
    kappa : float
        Plasma elongation (default 1.84).
    regulatory : str
        'lower' — fusion regulatory case (÷ 2.2 on nuclear buildings)
        'upper' — fission-like regulatory burden (no reduction)
    baseline : BuildingBaseline, optional
        Override default PWR12-BE reference costs.

    Returns
    -------
    StructuresCostResult

    Algorithm
    ---------
    1. Scale ALL baseline costs by (P_e_net / 1200)^0.6

    2. Within nuclear buildings, scale the reactor-building portion
       by the torus volume ratio (V_fusion / V_ITER)^0.6.
       This captures that compact HTS tokamaks need a smaller
       tokamak hall than ITER's LTS machine.  Other nuclear 
       buildings (hot cell, tritium, radwaste, control room, cryo)
       scale only with power.

    3. Divide nuclear building costs by 2.2 for lower bound
       (fusion earns lighter regulatory framework per NRC 10 CFR 30).
       Upper bound retains fission-like costs.

    4. Conventional buildings (turbine hall, cooling, electrical,
       admin, site improvements) scale only with power — no 
       regulatory or volume adjustment.
    """
    if baseline is None:
        baseline = DEFAULT_BASELINE

    # ── Step 1: Power scaling ──
    f_power = (P_e_net / PWR12_PE) ** N_SCALE

    # ── Step 2: Reactor building volume adjustment ──
    V_iter   = ITER_R0 * ITER_A**2 * ITER_KAPPA
    V_fusion = R0 * a**2 * kappa
    vol_ratio = V_fusion / V_iter
    f_vol = vol_ratio ** N_SCALE

    # Nuclear buildings at plant size:
    #   reactor bldg portion:  baseline × f_power × f_vol
    #   other nuclear portion: baseline × f_power × 1.0
    f_rb = baseline.reactor_bldg_fraction
    nuclear_scaled = (baseline.nuclear_total * f_power *
                      (f_rb * f_vol + (1.0 - f_rb)))

    # Conventional buildings at plant size:
    conven_scaled = baseline.conventional_total * f_power

    # ── Step 3: Regulatory adjustment ──
    reg_div = REG_FACTOR if regulatory == 'lower' else 1.0
    nuclear_final = nuclear_scaled / reg_div

    # ── Step 4: Totals ──
    total_M = nuclear_final + conven_scaled
    per_kW = (total_M * 1e6) / (P_e_net * 1e3)

    return StructuresCostResult(
        nuclear_buildings_M=nuclear_final,
        conventional_buildings_M=conven_scaled,
        total_structures_M=total_M,
        total_structures_per_kW=per_kW,
        power_scale_factor=f_power,
        volume_ratio=vol_ratio,
        reactor_bldg_vol_factor=f_vol,
        regulatory_divisor=reg_div,
    )


# ═══════════════════════════════════════════════════════════════════════
# DEMO / VALIDATION
# ═══════════════════════════════════════════════════════════════════════

if __name__ == '__main__':

    print("=" * 65)
    print("  ACCOUNT 21: STRUCTURES & SITE FACILITIES")
    print("  Araiinejad (2024/2025) NCET/EEDB Methodology")
    print("=" * 65)

    # ── Validation: reproduce ARAI Table 17 ──
    print("\n  CALIBRATION CHECK (ARAI @ 350 MWe, R0=3.3m, a=1.13m)")
    print("  " + "-" * 50)
    for bound, target in [('lower', 819), ('upper', 1317)]:
        r = structures_cost(350, 3.3, 1.13, 1.84, bound)
        err = abs(r.total_structures_per_kW - target)
        status = "✓" if err < 1 else f"✗ (off by {err:.0f})"
        print(f"  {bound.upper():>6s}: {r.total_structures_per_kW:>6,.0f} $/kW  "
              f"(target: {target})  {status}")

    # ── Parametric: vary P_e_net ──
    print(f"\n  SWEEP: P_e_net (R0=3.3m, a=1.13m, kappa=1.84)")
    print("  " + "-" * 50)
    print(f"  {'P_e [MWe]':>10s}  {'Lower $/kW':>12s}  {'Upper $/kW':>12s}"
          f"  {'Lower $M':>10s}  {'Upper $M':>10s}")
    for Pe in [100, 200, 350, 500, 750, 1000, 1500]:
        rl = structures_cost(Pe, 3.3, 1.13, 1.84, 'lower')
        ru = structures_cost(Pe, 3.3, 1.13, 1.84, 'upper')
        print(f"  {Pe:>10d}  {rl.total_structures_per_kW:>12,.0f}  "
              f"{ru.total_structures_per_kW:>12,.0f}  "
              f"{rl.total_structures_M:>10,.0f}  {ru.total_structures_M:>10,.0f}")

    # ── Parametric: vary machine size at 350 MWe ──
    print(f"\n  SWEEP: Reactor size (P_e=350 MWe, kappa=1.84)")
    print("  " + "-" * 50)
    print(f"  {'R0 [m]':>8s}  {'a [m]':>6s}  {'A':>5s}  {'V/V_ITER':>9s}  "
          f"{'Lower $/kW':>12s}  {'Upper $/kW':>12s}")
    for R0, a_val in [(2.0, 0.67), (3.3, 1.13), (4.5, 1.5),
                       (6.2, 2.0), (8.0, 2.5)]:
        rl = structures_cost(350, R0, a_val, 1.84, 'lower')
        ru = structures_cost(350, R0, a_val, 1.84, 'upper')
        A = R0 / a_val
        print(f"  {R0:>8.1f}  {a_val:>6.2f}  {A:>5.1f}  {rl.volume_ratio:>9.3f}  "
              f"{rl.total_structures_per_kW:>12,.0f}  "
              f"{ru.total_structures_per_kW:>12,.0f}")

    # ── Full output for ARAI baseline ──
    print(f"\n  FULL OUTPUT (ARAI lower bound):")
    print("  " + "-" * 50)
    r = structures_cost(350, 3.3, 1.13, 1.84, 'lower')
    for line in repr(r).split('\n'):
        print(f"  {line}")

    print()
