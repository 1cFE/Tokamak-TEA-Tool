"""TF coil iterative design and cost model.

Iterates on TF coil thickness to find a self-consistent solution for:
    - Winding pack thickness (from J_wp and total ampere-turns)
    - Structural thickness (from Lorentz hoop stress at B_peak)
    - Self-consistent B_t (from B_peak × R_inner / R0)

Cost model from:
    Araiinejad et al., "Levelized cost of electricity for a fusion power plant"
    NOAK REBCO cost: 30 USD/kA·m
"""

from dataclasses import dataclass
import numpy as np

from tokamak_sizing.sizing import SizingResult, SizingInputs
from tokamak_sizing import constants


@dataclass
class CoilResult:
    """TF coil design and cost."""
    delta_tf_wp_m: float       # Winding pack thickness [m]
    delta_tf_struc_m: float    # Structural thickness [m]
    delta_tf_total_m: float    # Total TF coil thickness [m]
    r_inner_m: float           # TF coil inner leg radius [m]
    b_t_self_consistent: float # Self-consistent B_t [T]
    ni_total_at: float         # Total ampere-turns [A·turns]
    length_per_turn_m: float   # Length per TF turn [m]
    cost_usd: float            # TF coil cost [USD]
    converged: bool            # Whether iteration converged
    iterations: int            # Number of iterations


def calculate_coils(
    sizing: SizingResult,
    inputs: SizingInputs,
    blanket_shield_thickness_m: float,
    *,
    j_wp_a_mm2: float = 150.0,
    gap_margin: float = 1.05,
    cost_per_kam: float = 30.0,
    packing_factor: float = 1.7,
    margin_m: float = 0.6,
    max_iter: int = 50,
    tol_m: float = 0.01,
) -> CoilResult:
    """Iterate TF coil thickness and compute cost.

    Parameters
    ----------
    blanket_shield_thickness_m : float
        Combined blanket + shielding thickness on the inboard side [m].
    j_wp_a_mm2 : float
        Winding pack current density [A/mm²]. Default 150 for REBCO.
    gap_margin : float
        Multiplier on (structural + winding pack) for gaps/insulation.
    cost_per_kam : float
        NOAK REBCO cost [USD/kA·m]. Default 30 (Araiinejad).
    packing_factor : float
        Accounts for non-REBCO volume in winding pack. Default 1.7.
    margin_m : float
        Engineering margin factor (typical 0.6, so 1/m ~ 1.67).
    """
    r0 = sizing.r_major_m
    a = r0 / inputs.aspect
    kappa = inputs.kappa
    b_peak = inputs.b_peak_t
    sigma_tf = inputs.sigma_tf_mpa * 1e6  # Pa
    mu0 = constants.RMU0

    # Convert J_wp to A/m²
    j_wp = j_wp_a_mm2 * 1e6  # A/mm² → A/m²

    delta_tf = 0.4  # initial guess [m]
    converged = False
    n_iter = 0

    for n_iter in range(1, max_iter + 1):
        r_inner = r0 - a - blanket_shield_thickness_m - delta_tf / 2.0

        if r_inner <= 0:
            # Cannot fit — return with unconverged flag
            return CoilResult(
                delta_tf_wp_m=0.0, delta_tf_struc_m=0.0,
                delta_tf_total_m=delta_tf, r_inner_m=0.0,
                b_t_self_consistent=0.0, ni_total_at=0.0,
                length_per_turn_m=0.0, cost_usd=0.0,
                converged=False, iterations=n_iter,
            )

        b_t = b_peak * r_inner / r0
        ni_total = b_t * 2.0 * np.pi * r0 / mu0

        # Winding pack thickness
        delta_tf_wp = ni_total / (j_wp * 2.0 * a * kappa)

        # Structural thickness (Lorentz hoop stress)
        delta_tf_struc = b_peak**2 * r_inner / (2.0 * mu0 * sigma_tf)

        delta_tf_new = (delta_tf_struc + delta_tf_wp) * gap_margin

        if abs(delta_tf_new - delta_tf) < tol_m:
            delta_tf = delta_tf_new
            converged = True
            break

        delta_tf = delta_tf_new

    # Recompute final values at converged thickness
    r_inner = r0 - a - blanket_shield_thickness_m - delta_tf / 2.0
    b_t = b_peak * r_inner / r0 if r_inner > 0 else 0.0
    ni_total = b_t * 2.0 * np.pi * r0 / mu0

    # Cost: TF_cost = cost_per_kAm × NI × length × (1/m) × packing × 0.001
    length_per_turn = 2.0 * np.pi * r0 + 4.0 * a * kappa
    tf_cost = (
        cost_per_kam
        * ni_total
        * length_per_turn
        * (1.0 / margin_m)
        * packing_factor
        * 0.001  # A → kA
    )

    return CoilResult(
        delta_tf_wp_m=delta_tf_wp,
        delta_tf_struc_m=delta_tf_struc,
        delta_tf_total_m=delta_tf,
        r_inner_m=r_inner,
        b_t_self_consistent=b_t,
        ni_total_at=ni_total,
        length_per_turn_m=length_per_turn,
        cost_usd=tf_cost,
        converged=converged,
        iterations=n_iter,
    )
