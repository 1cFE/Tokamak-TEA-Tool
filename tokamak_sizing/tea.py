"""Techno-Economic Analysis (TEA) and LCOE calculator for D-T tokamak FPP.

Calculates the Levelized Cost of Electricity by:
    1. Sizing the reactor with TokamakSizeOptimizatIonTool
    2. Costing each major component (FW, blanket, shielding, coils, buildings)
    3. Adding indirect costs (19-38% of direct) and replacement costs (11-107 USD/MWh)
    4. Computing discounted LCOE = Σ(costs/(1+r)^t) / Σ(energy/(1+r)^t)

Usage:
    from tokamak_sizing.tea import TEAInputs, calculate_lcoe
    result = calculate_lcoe(TEAInputs(...))
"""

import math
from dataclasses import dataclass, field

from tokamak_sizing.sizing import SizingInputs, SizingResult, TokamakSizeOptimizatIonTool
from tokamak_sizing.component_costs import (
    FWResult, BlanketResult, ShieldingResult,
    calculate_fw, calculate_blanket, calculate_shielding,
)
from tokamak_sizing.coil_costs import CoilResult, calculate_coils
from tokamak_sizing.buildings_cost import BuildingsCostResult, calculate_buildings
from tokamak_sizing.materials import (
    FW_MATERIALS, BLANKET_FW_DEFAULTS, BLANKET_COOLANT_TEMP_K,
    BLANKET_TEA_PARAMS, SHIELD_MATERIALS, SC_FLUENCE_LIMITS,
    SC_COIL_PARAMS,
)


# ---------------------------------------------------------------------------
# Input / output dataclasses
# ---------------------------------------------------------------------------

@dataclass
class TEAInputs:
    """All inputs for the TEA / LCOE calculation.

    Material properties (FW, blanket, shield, coil) are auto-resolved from
    high-level selections (fw_material, shield_material, blanket_type, sc_type).
    Set any property to a non-None value to override the lookup.
    """

    # --- Reactor sizing ---
    sizing_inputs: SizingInputs = None

    # --- Material selections ---
    fw_material: str = None            # FW material (None = auto from blanket_type)
    shield_material: str = "SS316"     # Shield material (key into SHIELD_MATERIALS)

    # --- First wall (None = auto-resolve from fw_material + blanket_type) ---
    t_max_fw_k: float = None           # Max FW temperature [K]
    t_coolant_k: float = None          # FW coolant temperature [K]
    k_fw_w_mk: float = None            # FW thermal conductivity [W/m/K]
    rho_fw: float = None               # FW density [kg/m³]
    cost_fw_per_kg: float = None       # Fabricated FW material [USD/kg]
    f_wall: float = 0.3                # Fraction of SOL power to main wall

    # --- Blanket (None = auto-resolve from blanket_type) ---
    rho_blanket_avg: float = None      # Blanket avg density [kg/m³]
    cost_blanket_per_kg: float = None  # Blanket module cost [USD/kg]

    # --- Shielding / VV (None = auto-resolve from shield_material + sc_type) ---
    sigma_r_cm: float = None           # Removal cross-section [1/cm]
    fluence_limit: float = None        # SC cumulative fluence limit [n/m²]
    rho_shield: float = None           # Shield density [kg/m³]
    cost_shield_per_kg: float = None   # Fabricated shield [USD/kg]

    # --- TF coils (None = auto-resolve from sc_type) ---
    j_wp_a_mm2: float = None           # Winding pack J [A/mm²]
    cost_per_kam: float = None         # SC conductor cost [USD/kA·m]
    gap_margin: float = 1.05           # TF gap/insulation margin
    packing_factor: float = 1.7        # Non-SC volume in winding pack
    coil_margin_m: float = 0.6         # Engineering margin (1/m ~ 1.67)

    # --- Operations ---
    capacity_factor: float = 0.85      # Plant capacity factor (0-1)
    project_lifespan_yr: float = 30.0  # Plant lifetime [years]

    # --- Replacement costs (Araiinejad bounds) ---
    replacement_cost_low: float = 11.0   # [USD/MWh]
    replacement_cost_high: float = 107.0 # [USD/MWh]

    # --- Indirect costs ---
    indirect_cost_frac_low: float = 0.19   # 19% of direct costs
    indirect_cost_frac_high: float = 0.38  # 38% of direct costs

    # --- Fluence / replacement interval ---
    allowable_blanket_fluence: float = 25.0  # [MW·yr/m²]
    nwl_peak: float = 10.0                   # Peak neutron wall load [MW/m²]

    # --- Turbine & BoP equipment (pyFECONS flat rates on gross electric) ---
    turbine_cost_per_kw: float = 267.0  # USD/kW_gross (pyFECONS)
    bop_cost_per_kw: float = 197.0      # USD/kW_gross (pyFECONS)

    # --- Discount rate ---
    discount_rate: float = 0.08         # Annual discount rate (default 8%)

    # --- Regulation ---
    high_regulation_mode: bool = False  # 2.2× building costs, 0.8× CF

    def __post_init__(self):
        """Resolve material properties from lookup tables.

        Any field left as None is populated from the appropriate material
        database.  Explicit (non-None) values are never overwritten.
        """
        si = self.sizing_inputs
        blanket_type = si.blanket_type if si is not None else "WCLL"
        sc_type = si.sc_type if si is not None else "REBCO"

        # --- FW material ---
        if self.fw_material is None:
            self.fw_material = BLANKET_FW_DEFAULTS.get(blanket_type, "W")
        if self.fw_material not in FW_MATERIALS:
            raise ValueError(
                f"Unknown fw_material '{self.fw_material}'. "
                f"Choose from: {list(FW_MATERIALS.keys())}"
            )
        fw = FW_MATERIALS[self.fw_material]
        if self.t_max_fw_k is None:
            self.t_max_fw_k = fw["t_max_k"]
        if self.k_fw_w_mk is None:
            self.k_fw_w_mk = fw["k_w_mk"]
        if self.rho_fw is None:
            self.rho_fw = fw["rho"]
        if self.cost_fw_per_kg is None:
            self.cost_fw_per_kg = fw["cost_per_kg"]

        # --- Coolant temperature from blanket type ---
        if self.t_coolant_k is None:
            self.t_coolant_k = BLANKET_COOLANT_TEMP_K.get(blanket_type, 673.0)

        # --- Blanket TEA properties ---
        if blanket_type in BLANKET_TEA_PARAMS:
            bp_tea = BLANKET_TEA_PARAMS[blanket_type]
            if self.rho_blanket_avg is None:
                self.rho_blanket_avg = bp_tea["rho_avg"]
            if self.cost_blanket_per_kg is None:
                self.cost_blanket_per_kg = bp_tea["cost_per_kg"]
        else:
            if self.rho_blanket_avg is None:
                self.rho_blanket_avg = 7770.0
            if self.cost_blanket_per_kg is None:
                self.cost_blanket_per_kg = 200.0

        # --- Shield material ---
        if self.shield_material not in SHIELD_MATERIALS:
            raise ValueError(
                f"Unknown shield_material '{self.shield_material}'. "
                f"Choose from: {list(SHIELD_MATERIALS.keys())}"
            )
        sm = SHIELD_MATERIALS[self.shield_material]
        if self.sigma_r_cm is None:
            self.sigma_r_cm = sm["sigma_r_cm"]
        if self.rho_shield is None:
            self.rho_shield = sm["rho"]
        if self.cost_shield_per_kg is None:
            self.cost_shield_per_kg = sm["cost_per_kg"]

        # --- Fluence limit from SC type ---
        if self.fluence_limit is None:
            self.fluence_limit = SC_FLUENCE_LIMITS.get(sc_type, 1e22)

        # --- TF coil TEA properties from SC type ---
        if sc_type in SC_COIL_PARAMS:
            sc_tea = SC_COIL_PARAMS[sc_type]
            if self.j_wp_a_mm2 is None:
                self.j_wp_a_mm2 = sc_tea["j_wp_a_mm2"]
            if self.cost_per_kam is None:
                self.cost_per_kam = sc_tea["cost_per_kam"]
        else:
            if self.j_wp_a_mm2 is None:
                self.j_wp_a_mm2 = 150.0
            if self.cost_per_kam is None:
                self.cost_per_kam = 30.0


@dataclass
class TEAResult:
    """Full TEA / LCOE output."""

    # Sizing
    sizing: SizingResult = None

    # Component results
    fw: FWResult = None
    blanket: BlanketResult = None
    shielding: ShieldingResult = None
    coils: CoilResult = None
    buildings: BuildingsCostResult = None

    # Turbine & BoP equipment
    turbine_cost_usd: float = 0.0
    bop_cost_usd: float = 0.0

    # Cost aggregates [USD]
    direct_cost_usd: float = 0.0
    indirect_cost_low_usd: float = 0.0
    indirect_cost_high_usd: float = 0.0
    replacement_cost_low_usd: float = 0.0
    replacement_cost_high_usd: float = 0.0

    # CAPEX = direct + indirect
    capex_low_usd: float = 0.0
    capex_high_usd: float = 0.0

    # Energy
    energy_throughput_mwh: float = 0.0

    # LCOE [USD/MWh]
    lcoe_nominal_usd_mwh: float = 0.0     # Low replacement + low indirect
    lcoe_high_reg_usd_mwh: float = 0.0    # High replacement + high indirect + regulation

    # Discount rate
    discount_rate: float = 0.0
    annuity_factor: float = 0.0            # Σ 1/(1+r)^t for t=1..N

    # Capacity factor / replacement
    replacement_interval_yr: float = 0.0
    limiting_component: str = ""
    required_replacement_time_months: float = 0.0
    replacement_time_risk: bool = False

    # For pie chart
    cost_breakdown: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Main LCOE calculation
# ---------------------------------------------------------------------------

def calculate_lcoe(tea: TEAInputs) -> TEAResult:
    """Run the full TEA: sizing → component costs → LCOE."""

    si = tea.sizing_inputs

    # 1. Size the reactor
    sizing = TokamakSizeOptimizatIonTool(si)

    # 2. Component costs
    fw = calculate_fw(
        sizing, si,
        t_max_fw_k=tea.t_max_fw_k,
        t_coolant_k=tea.t_coolant_k,
        k_tungsten=tea.k_fw_w_mk,
        rho_tungsten=tea.rho_fw,
        cost_per_kg=tea.cost_fw_per_kg,
        f_wall=tea.f_wall,
    )

    blanket = calculate_blanket(
        sizing, si,
        rho_blanket_avg=tea.rho_blanket_avg,
        cost_per_kg=tea.cost_blanket_per_kg,
    )

    shielding = calculate_shielding(
        sizing, si, blanket,
        sigma_r_cm=tea.sigma_r_cm,
        fluence_limit=tea.fluence_limit,
        rho_shield=tea.rho_shield,
        cost_per_kg=tea.cost_shield_per_kg,
        capacity_factor=tea.capacity_factor,
        project_lifespan_yr=tea.project_lifespan_yr,
    )

    blanket_shield_thickness = blanket.total_thickness_m + shielding.shield_thickness_m

    coils = calculate_coils(
        sizing, si,
        blanket_shield_thickness_m=blanket_shield_thickness,
        j_wp_a_mm2=tea.j_wp_a_mm2,
        gap_margin=tea.gap_margin,
        cost_per_kam=tea.cost_per_kam,
        packing_factor=tea.packing_factor,
        margin_m=tea.coil_margin_m,
    )

    buildings = calculate_buildings(
        sizing, si,
        high_regulation_mode=False,  # nominal uses fusion regulatory discount
    )

    # 3. Turbine & BoP equipment (flat rate on gross electric power)
    turbine_cost = tea.turbine_cost_per_kw * sizing.p_gross_mw * 1e3  # MW→kW
    bop_cost = tea.bop_cost_per_kw * sizing.p_gross_mw * 1e3

    # 4. Direct costs
    direct = (fw.cost_usd + blanket.cost_usd + shielding.cost_usd
              + coils.cost_usd + buildings.total_usd
              + turbine_cost + bop_cost)

    # 4. Indirect costs
    indirect_low = direct * tea.indirect_cost_frac_low
    indirect_high = direct * tea.indirect_cost_frac_high

    # 5. CAPEX
    capex_low = direct + indirect_low
    capex_high = direct + indirect_high

    # 6. Capacity factor and replacement interval
    replacement_interval = tea.allowable_blanket_fluence / tea.nwl_peak
    limiting_component = "blanket"

    # Required downtime per replacement cycle
    # In each replacement_interval, uptime = interval × CF
    # downtime = interval × (1 - CF)
    downtime_yr = replacement_interval * (1.0 - tea.capacity_factor)
    downtime_months = downtime_yr * 12.0
    replacement_risk = downtime_months < 1.0

    # 7. Discount factor
    # Annuity factor AF = Σ_{t=1}^{N} 1/(1+r)^t
    # For r > 0: AF = (1 - (1+r)^{-N}) / r
    # For r = 0: AF = N (undiscounted)
    r = tea.discount_rate
    n = int(tea.project_lifespan_yr)
    if r > 0:
        annuity_factor = (1.0 - (1.0 + r) ** (-n)) / r
    else:
        annuity_factor = float(n)

    # 8. Discounted LCOE
    # CAPEX is incurred at t=0 (no discounting).
    # Energy is produced annually → discounted by annuity factor.
    # Replacements are discrete lump sums at each replacement interval,
    # discounted to the year they occur.
    #
    # Cost per replacement = repl_rate [$/MWh] × energy_per_interval [MWh]
    # PV of replacements = Σ_{k=1}^{N_repl} C_repl / (1+r)^(k × interval)

    def _pv_replacements(repl_rate: float, energy_per_interval: float,
                         interval_yr: float, lifespan_yr: float,
                         discount_rate: float) -> float:
        """Present value of discrete replacement costs at each interval."""
        cost_per_replacement = repl_rate * energy_per_interval
        n_repl = int(lifespan_yr / interval_yr)
        pv = 0.0
        for k in range(1, n_repl + 1):
            t = k * interval_yr
            if t > lifespan_yr:
                break
            if discount_rate > 0:
                pv += cost_per_replacement / (1.0 + discount_rate) ** t
            else:
                pv += cost_per_replacement
        return pv

    # --- Nominal scenario ---
    energy_annual_nom = si.p_net_mw * tea.capacity_factor * 8760.0  # MWh/yr
    energy_nominal = energy_annual_nom * tea.project_lifespan_yr     # undiscounted total
    discounted_energy_nom = energy_annual_nom * annuity_factor       # PV of energy

    energy_per_interval_nom = energy_annual_nom * replacement_interval
    repl_low_nominal = _pv_replacements(
        tea.replacement_cost_low, energy_per_interval_nom,
        replacement_interval, tea.project_lifespan_yr, r)
    lcoe_nominal = (capex_low + repl_low_nominal) / discounted_energy_nom

    # --- High regulation scenario ---
    # Nuclear buildings ×2.2 (remove fusion discount); CF ×0.8
    buildings_reg_usd = (buildings.nuclear_island_cost_usd * 2.2
                         + buildings.conventional_buildings_cost_usd)
    direct_reg = (fw.cost_usd + blanket.cost_usd + shielding.cost_usd
                  + coils.cost_usd + buildings_reg_usd
                  + turbine_cost + bop_cost)
    indirect_reg = direct_reg * tea.indirect_cost_frac_high
    capex_reg = direct_reg + indirect_reg

    cf_reg = tea.capacity_factor * 0.8
    energy_annual_reg = si.p_net_mw * cf_reg * 8760.0
    discounted_energy_reg = energy_annual_reg * annuity_factor

    energy_per_interval_reg = energy_annual_reg * replacement_interval
    repl_high_reg = _pv_replacements(
        tea.replacement_cost_high, energy_per_interval_reg,
        replacement_interval, tea.project_lifespan_yr, r)
    lcoe_high_reg = (capex_reg + repl_high_reg) / discounted_energy_reg

    # Cost breakdown for pie chart (nominal scenario)
    cost_breakdown = {
        "First Wall": fw.cost_usd,
        "Blanket": blanket.cost_usd,
        "Shielding/VV": shielding.cost_usd,
        "TF Coils": coils.cost_usd,
        "Buildings": buildings.total_usd,
        "Turbine": turbine_cost,
        "BoP": bop_cost,
        "Indirect": indirect_low,
        "Replacement": repl_low_nominal,
    }

    return TEAResult(
        sizing=sizing,
        fw=fw,
        blanket=blanket,
        shielding=shielding,
        coils=coils,
        buildings=buildings,
        turbine_cost_usd=turbine_cost,
        bop_cost_usd=bop_cost,
        direct_cost_usd=direct,
        indirect_cost_low_usd=indirect_low,
        indirect_cost_high_usd=indirect_high,
        replacement_cost_low_usd=repl_low_nominal,
        replacement_cost_high_usd=repl_high_reg,
        capex_low_usd=capex_low,
        capex_high_usd=capex_reg,
        energy_throughput_mwh=energy_nominal,
        lcoe_nominal_usd_mwh=lcoe_nominal,
        lcoe_high_reg_usd_mwh=lcoe_high_reg,
        discount_rate=r,
        annuity_factor=annuity_factor,
        replacement_interval_yr=replacement_interval,
        limiting_component=limiting_component,
        required_replacement_time_months=downtime_months,
        replacement_time_risk=replacement_risk,
        cost_breakdown=cost_breakdown,
    )
