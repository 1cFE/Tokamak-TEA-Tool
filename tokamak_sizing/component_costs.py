"""Component cost models for first wall, blanket, and shielding/VV.

Cost data sources:
    - Tungsten (fabricated PFC): ~150 USD/kg
      Federici et al., "Overview of the DEMO staged design approach in Europe",
      Nucl. Fusion 59 (2019) 066013
    - WCLL blanket modules: ~200 USD/kg
      Bachmann et al., EU-DEMO blanket cost estimates (2024)
    - Steel shielding (fabricated SS316): ~30 USD/kg
      Industrial fabrication estimates for nuclear-grade stainless steel
"""

from dataclasses import dataclass
import numpy as np

from tokamak_sizing.sizing import (
    SizingResult,
    SizingInputs,
    BLANKET_PARAMS,
    compute_breeding_zone_thickness,
    compute_first_wall_area,
)
from tokamak_sizing import constants


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------

@dataclass
class FWResult:
    """First wall sizing and cost."""
    q_surface_mw_m2: float   # Surface heat flux [MW/m²]
    thickness_m: float       # FW thickness [m]
    area_m2: float           # First wall area [m²]
    volume_m3: float         # FW volume [m³]
    mass_kg: float           # FW mass [kg]
    cost_usd: float          # FW cost [USD]


@dataclass
class BlanketResult:
    """Blanket sizing and cost."""
    breeding_zone_m: float       # Breeding zone thickness [m]
    struct_overhead_m: float     # Structural overhead [m]
    total_thickness_m: float     # Total blanket thickness [m]
    volume_m3: float             # Blanket volume [m³]
    mass_kg: float               # Blanket mass [kg]
    cost_usd: float              # Blanket cost [USD]


@dataclass
class ShieldingResult:
    """Shielding/VV sizing and cost."""
    neutron_flux_n_m2_s: float       # Neutron flux at FW [n/m²/s]
    lifetime_fluence_n_m2: float     # Cumulative fluence at FW [n/m²]
    total_atten_thickness_m: float   # Total steel-equivalent attenuation needed [m]
    blanket_credit_m: float          # Blanket structural thickness credit [m]
    shield_thickness_m: float        # Dedicated shield + VV thickness [m]
    volume_m3: float                 # Shield volume [m³]
    mass_kg: float                   # Shield mass [kg]
    cost_usd: float                  # Shield cost [USD]


# ---------------------------------------------------------------------------
# First wall
# ---------------------------------------------------------------------------

def calculate_fw(
    sizing: SizingResult,
    inputs: SizingInputs,
    *,
    t_max_fw_k: float = 1473.0,
    t_coolant_k: float = 673.0,
    k_tungsten: float = 170.0,
    rho_tungsten: float = 19300.0,
    cost_per_kg: float = 150.0,
    f_wall: float = 0.3,
    f_rad: float = None,
    max_thickness_m: float = 0.005,
) -> FWResult:
    """Calculate first wall thickness, mass, and cost.

    FW thickness derived from Fourier's law for a flat slab:
        t_fw = k_W * delta_T / q_surface

    This gives the *maximum allowable* thickness before exceeding the
    temperature limit. The actual design thickness is capped at
    max_thickness_m (default 5 mm, typical for W armor tiles).

    Parameters
    ----------
    f_wall : float
        Fraction of SOL power reaching the main wall (rest goes to divertor).
    max_thickness_m : float
        Practical cap on FW thickness [m]. Default 5 mm (typical W armor).
    """
    if f_rad is None:
        f_rad = inputs.f_rad

    a = sizing.r_major_m / inputs.aspect
    a_fw = compute_first_wall_area(sizing.r_major_m, a, inputs.kappa)

    # Surface heat flux on the first wall [W/m²]
    p_sol_mw = sizing.power_balance.p_loss_mw * (1.0 - f_rad)
    q_surface_w = p_sol_mw * 1e6 * f_wall / a_fw

    # FW thickness from Fourier's law (max allowable before exceeding ΔT)
    delta_t = t_max_fw_k - t_coolant_k
    t_fw_thermal = k_tungsten * delta_t / q_surface_w

    # Cap at practical design thickness
    t_fw = min(t_fw_thermal, max_thickness_m)

    volume = t_fw * a_fw
    mass = rho_tungsten * volume
    cost = mass * cost_per_kg

    return FWResult(
        q_surface_mw_m2=q_surface_w / 1e6,
        thickness_m=t_fw,
        area_m2=a_fw,
        volume_m3=volume,
        mass_kg=mass,
        cost_usd=cost,
    )


# ---------------------------------------------------------------------------
# Blanket
# ---------------------------------------------------------------------------

def calculate_blanket(
    sizing: SizingResult,
    inputs: SizingInputs,
    *,
    rho_blanket_avg: float = 7770.0,
    cost_per_kg: float = 200.0,
) -> BlanketResult:
    """Calculate blanket volume, mass, and cost.

    Breeding zone thickness from Chiletti et al. TBR model (WCLL) or
    default 0.70 m for blanket types without a TBR model.

    rho_blanket_avg default 7770 kg/m³ for WCLL:
        ~60% PbLi (9700 kg/m³) + ~25% EUROFER (7800 kg/m³) + ~15% void
    """
    bp = BLANKET_PARAMS[inputs.blanket_type]

    # Breeding zone thickness
    if bp["tbr_sat"] is not None:
        tbr_local = inputs.tbr_target / (1.0 - inputs.f_hole)
        if tbr_local >= bp["tbr_sat"]:
            tbr_local = bp["tbr_sat"] * 0.95
        bz = compute_breeding_zone_thickness(
            tbr_local, bp["tbr_sat"], bp["tbr_t0_cm"],
            bp["tbr_alpha"], bp["tbr_beta"], bp["tbr_lambda"],
        )
    else:
        bz = inputs.blanket_thickness_m - bp["struct_overhead_m"]

    struct_overhead = bp["struct_overhead_m"]
    total_thickness = bz + struct_overhead

    a = sizing.r_major_m / inputs.aspect
    a_fw = compute_first_wall_area(sizing.r_major_m, a, inputs.kappa)

    volume = total_thickness * a_fw * (1.0 - inputs.f_hole)
    mass = volume * rho_blanket_avg
    cost = mass * cost_per_kg

    return BlanketResult(
        breeding_zone_m=bz,
        struct_overhead_m=struct_overhead,
        total_thickness_m=total_thickness,
        volume_m3=volume,
        mass_kg=mass,
        cost_usd=cost,
    )


# ---------------------------------------------------------------------------
# Shielding / VV
# ---------------------------------------------------------------------------

def calculate_shielding(
    sizing: SizingResult,
    inputs: SizingInputs,
    blanket: BlanketResult,
    *,
    sigma_r_cm: float = 0.096,
    fluence_limit: float = 1e22,
    rho_shield: float = 7800.0,
    cost_per_kg: float = 30.0,
    capacity_factor: float = 0.85,
    project_lifespan_yr: float = 30.0,
) -> ShieldingResult:
    """Calculate shielding/VV thickness to protect TF coils from neutron damage.

    Steps:
        1. Neutron flux at FW from P_neutron and 14.1 MeV per neutron (DT).
        2. Lifetime fluence = flux × CF × lifespan.
        3. Total steel-equivalent attenuation from exponential shielding law.
        4. Credit blanket structural thickness, derive dedicated shield.

    sigma_r = 0.096/cm is the macroscopic removal cross-section for steel
    (includes all non-breeding structural material: blanket structure + VV + shield).
    """
    # DT neutron energy: 14.1 MeV
    e_neutron_j = 14.1e6 * constants.ELECTRON_VOLT

    a = sizing.r_major_m / inputs.aspect
    a_fw = compute_first_wall_area(sizing.r_major_m, a, inputs.kappa)

    # Neutron flux at first wall [n/m²/s]
    p_neutron_w = sizing.power_balance.p_neutron_mw * 1e6
    phi = p_neutron_w / (e_neutron_j * a_fw)

    # Cumulative lifetime fluence at first wall [n/m²]
    seconds_per_year = 3.156e7
    f_wall = phi * capacity_factor * project_lifespan_yr * seconds_per_year

    if f_wall <= fluence_limit:
        return ShieldingResult(
            neutron_flux_n_m2_s=phi,
            lifetime_fluence_n_m2=f_wall,
            total_atten_thickness_m=0.0,
            blanket_credit_m=0.0,
            shield_thickness_m=0.0,
            volume_m3=0.0,
            mass_kg=0.0,
            cost_usd=0.0,
        )

    # Total steel-equivalent attenuation thickness [m]
    sigma_r_m = sigma_r_cm * 100.0  # convert /cm to /m
    t_total = np.log(f_wall / fluence_limit) / sigma_r_m

    # Credit blanket structural thickness
    blanket_credit = blanket.struct_overhead_m
    t_shield = max(t_total - blanket_credit, 0.0)

    # Shield volume — approximate using FW area at blanket outer surface
    volume = t_shield * a_fw
    mass = volume * rho_shield
    cost = mass * cost_per_kg

    return ShieldingResult(
        neutron_flux_n_m2_s=phi,
        lifetime_fluence_n_m2=f_wall,
        total_atten_thickness_m=t_total,
        blanket_credit_m=blanket_credit,
        shield_thickness_m=t_shield,
        volume_m3=volume,
        mass_kg=mass,
        cost_usd=cost,
    )
