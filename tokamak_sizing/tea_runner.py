"""Entry point for the Fusion TEA / LCOE calculator.

Run with:
    python3 -m tokamak_sizing.tea_runner
"""

import matplotlib
matplotlib.use("Agg")  # non-interactive backend
import matplotlib.pyplot as plt

from tokamak_sizing.sizing import SizingInputs
from tokamak_sizing.tea import TEAInputs, TEAResult, calculate_lcoe

# Scenario labels
LABEL_LOW = "Low LCOE Scenario: Minimal Regulatory + Replacement Costs"
LABEL_HIGH = "High LCOE Scenario: High Regulatory + Replacement Costs"
COL_LOW = "Low LCOE"
COL_HIGH = "High LCOE"


def fmt_usd(v: float) -> str:
    """Format USD with commas and no decimals for large values."""
    if abs(v) >= 1e9:
        return f"${v/1e9:,.2f} B"
    if abs(v) >= 1e6:
        return f"${v/1e6:,.1f} M"
    return f"${v:,.0f}"


def print_result(r: TEAResult, tea: TEAInputs):
    """Print the full TEA breakdown."""

    si = tea.sizing_inputs
    s = r.sizing

    print("=" * 72)
    print("  Fusion TEA / LCOE Calculator")
    print("=" * 72)

    # --- Reactor summary ---
    print("\n--- Reactor Sizing ---")
    print(f"  R_major     = {s.r_major_m:.2f} m")
    print(f"  a_minor     = {s.r_major_m / si.aspect:.2f} m")
    print(f"  B_t (sizing)= {si.b_t:.2f} T")
    print(f"  P_fusion    = {s.p_fusion_mw:.1f} MW")
    print(f"  P_net       = {si.p_net_mw:.1f} MW")
    print(f"  Binding     = {s.binding_constraint}")

    # --- First wall ---
    print(f"\n--- First Wall ({tea.fw_material}) ---")
    print(f"  q_surface   = {r.fw.q_surface_mw_m2:.3f} MW/m²")
    print(f"  Thickness   = {r.fw.thickness_m * 1000:.1f} mm  (capped at 5.0 mm design limit)")
    print(f"  Area        = {r.fw.area_m2:.1f} m²")
    print(f"  Mass        = {r.fw.mass_kg:,.0f} kg  ({r.fw.mass_kg/1000:.1f} t)")
    print(f"  Cost        = {fmt_usd(r.fw.cost_usd)}  @ ${tea.cost_fw_per_kg}/kg")

    # --- Blanket ---
    print(f"\n--- Blanket ({si.blanket_type}) ---")
    print(f"  Breeding zone  = {r.blanket.breeding_zone_m:.3f} m")
    print(f"  Struct overhead= {r.blanket.struct_overhead_m:.3f} m")
    print(f"  Total thick.   = {r.blanket.total_thickness_m:.3f} m")
    print(f"  Volume         = {r.blanket.volume_m3:.1f} m³")
    print(f"  Mass           = {r.blanket.mass_kg:,.0f} kg  ({r.blanket.mass_kg/1000:.1f} t)")
    print(f"  Cost           = {fmt_usd(r.blanket.cost_usd)}  @ ${tea.cost_blanket_per_kg}/kg")

    # --- Shielding ---
    print("\n--- Shielding / VV ---")
    print(f"  Neutron flux   = {r.shielding.neutron_flux_n_m2_s:.2e} n/m²/s")
    print(f"  Lifetime fluence = {r.shielding.lifetime_fluence_n_m2:.2e} n/m²  (limit: {tea.fluence_limit:.0e})")
    print(f"  Total atten.   = {r.shielding.total_atten_thickness_m:.3f} m")
    print(f"  Blanket credit = {r.shielding.blanket_credit_m:.3f} m")
    print(f"  Shield thick.  = {r.shielding.shield_thickness_m:.3f} m")
    print(f"  Mass           = {r.shielding.mass_kg:,.0f} kg  ({r.shielding.mass_kg/1000:.1f} t)")
    print(f"  Cost           = {fmt_usd(r.shielding.cost_usd)}  @ ${tea.cost_shield_per_kg}/kg ({tea.shield_material})")

    # --- TF Coils ---
    print(f"\n--- TF Coils ({si.sc_type}) ---")
    print(f"  Converged      = {r.coils.converged}  ({r.coils.iterations} iterations)")
    print(f"  Δ_TF_wp       = {r.coils.delta_tf_wp_m:.3f} m")
    print(f"  Δ_TF_struc    = {r.coils.delta_tf_struc_m:.3f} m")
    print(f"  Δ_TF_total    = {r.coils.delta_tf_total_m:.3f} m")
    print(f"  R_inner        = {r.coils.r_inner_m:.3f} m")
    print(f"  B_t (self-con) = {r.coils.b_t_self_consistent:.2f} T")
    print(f"  NI_total       = {r.coils.ni_total_at:.2e} A·turns")
    print(f"  Length/turn    = {r.coils.length_per_turn_m:.1f} m")
    print(f"  Cost           = {fmt_usd(r.coils.cost_usd)}  @ ${tea.cost_per_kam}/kA·m NOAK")

    # --- Buildings ---
    print("\n--- Buildings (Araiinejad NCET/EEDB) ---")
    print(f"  Nuclear island = {fmt_usd(r.buildings.nuclear_island_cost_usd)}  (fusion regulatory discount applied)")
    print(f"  Conventional   = {fmt_usd(r.buildings.conventional_buildings_cost_usd)}")
    print(f"  Total          = {fmt_usd(r.buildings.total_usd)}  ({r.buildings.cost_per_kw:.0f} $/kW)")
    print(f"  V/V_ITER       = {r.buildings.volume_ratio:.3f}")

    # --- Capacity factor & replacement ---
    print("\n--- Capacity Factor & Replacement ---")
    print(f"  Capacity factor    = {tea.capacity_factor:.0%}")
    print(f"  Replacement interval = {r.replacement_interval_yr:.1f} yr  (limited by: {r.limiting_component})")
    print(f"  Replacements       = {int(tea.project_lifespan_yr / r.replacement_interval_yr)}")
    risk_tag = "  *** RISK: < 1 month ***" if r.replacement_time_risk else ""
    print(f"  Downtime per cycle = {r.required_replacement_time_months:.1f} months{risk_tag}")

    # --- Cost summary ---
    print("\n" + "=" * 72)
    print("  COST SUMMARY")
    print("=" * 72)

    print(f"\n  Direct costs:")
    print(f"    First Wall     = {fmt_usd(r.fw.cost_usd)}")
    print(f"    Blanket        = {fmt_usd(r.blanket.cost_usd)}")
    print(f"    Shielding/VV   = {fmt_usd(r.shielding.cost_usd)}")
    print(f"    TF Coils       = {fmt_usd(r.coils.cost_usd)}")
    print(f"    Turbine equip. = {fmt_usd(r.turbine_cost_usd)}")
    print(f"    BoP equipment  = {fmt_usd(r.bop_cost_usd)}")
    print(f"    Buildings      = {fmt_usd(r.buildings.total_usd)}")
    print(f"    ─────────────────────────────")
    print(f"    TOTAL DIRECT   = {fmt_usd(r.direct_cost_usd)}")

    print(f"\n  Energy throughput  = {r.energy_throughput_mwh:,.0f} MWh  ({tea.project_lifespan_yr:.0f} yr × {tea.capacity_factor:.0%} CF)")
    print(f"  Discount rate      = {r.discount_rate:.0%}")
    print(f"  Annuity factor     = {r.annuity_factor:.3f}  (PV of $1/yr for {tea.project_lifespan_yr:.0f} yr)")

    # --- LCOE: Low scenario ---
    print(f"\n  ┌──────────────────────────────────────────────────────────────────┐")
    print(f"  │  {LABEL_LOW}")
    print(f"  │  LCOE = {r.lcoe_nominal_usd_mwh:.1f} USD/MWh")
    print(f"  └──────────────────────────────────────────────────────────────────┘")
    print(f"    CAPEX            = {fmt_usd(r.capex_low_usd)}")
    print(f"    Indirect ({tea.indirect_cost_frac_low:.0%})   = {fmt_usd(r.indirect_cost_low_usd)}")
    print(f"    Replacement (PV) = {fmt_usd(r.replacement_cost_low_usd)}  @ {tea.replacement_cost_low} USD/MWh")

    # --- LCOE: High scenario ---
    print(f"\n  ┌──────────────────────────────────────────────────────────────────┐")
    print(f"  │  {LABEL_HIGH}")
    print(f"  │  LCOE = {r.lcoe_high_reg_usd_mwh:.1f} USD/MWh")
    print(f"  └──────────────────────────────────────────────────────────────────┘")
    print(f"    CAPEX            = {fmt_usd(r.capex_high_usd)}")
    print(f"    Indirect ({tea.indirect_cost_frac_high:.0%})   = {fmt_usd(r.indirect_cost_high_usd)}")
    print(f"    Replacement (PV) = {fmt_usd(r.replacement_cost_high_usd)}  @ {tea.replacement_cost_high} USD/MWh")
    cf_reg = tea.capacity_factor * 0.8
    print(f"    CF (regulated)   = {cf_reg:.0%}")
    print(f"    Buildings ×2.2   = yes")

    print()


def print_summary_tables(r: TEAResult, tea: TEAInputs):
    """Print compact user-inputs table and two-column key-outputs table."""

    si = tea.sizing_inputs
    s = r.sizing
    W1 = 32   # label column width
    W2 = 18   # value column width

    # ===================================================================
    # USER-DEFINED INPUTS
    # ===================================================================
    print("=" * 72)
    print("  USER-DEFINED INPUTS")
    print("=" * 72)

    def _row(label: str, value: str):
        print(f"  {label:<{W1}} {value}")

    print("\n  Reactor Design")
    print(f"  {'─' * 50}")
    _row("Net electric power", f"{si.p_net_mw:.0f} MW")
    _row("Engineering gain Q_eng", f"{si.q_eng:.1f}")
    _row("Aspect ratio A", f"{si.aspect:.1f}")
    _row("Elongation κ", f"{si.kappa:.2f}")
    _row("Triangularity δ", f"{si.triang:.2f}")
    _row("Fuel", si.fuel_type)
    _row("B_t fraction of B_peak", f"{si.b_t_fraction:.2f}")

    print("\n  Physics Limits")
    print(f"  {'─' * 50}")
    _row("q95 min", f"{si.q95_min:.1f}")
    _row("β_N max", f"{si.beta_n_max:.2f}")
    _row("H98y2 max", f"{si.h_max:.1f}")
    _row("f_GW max", f"{si.f_gw_max:.2f}")

    print("\n  Material Selections")
    print(f"  {'─' * 50}")
    _row("Blanket type", si.blanket_type)
    _row("Superconductor", si.sc_type)
    _row("First wall material", tea.fw_material)
    _row("Shield material", tea.shield_material)

    print("\n  Efficiencies")
    print(f"  {'─' * 50}")
    _row("η_thermal", f"{si.eta_thermal:.2f}")
    _row("η_wall_plug", f"{si.eta_wall_plug:.2f}")
    _row("η_absorption", f"{si.eta_absorption:.2f}")

    print("\n  TEA / Economics")
    print(f"  {'─' * 50}")
    _row("Capacity factor", f"{tea.capacity_factor:.0%}")
    _row("Project lifespan", f"{tea.project_lifespan_yr:.0f} yr")
    _row("Discount rate", f"{tea.discount_rate:.0%}")
    _row("Indirect cost (low / high)", f"{tea.indirect_cost_frac_low:.0%} / {tea.indirect_cost_frac_high:.0%}")
    _row("Replacement cost (low / high)", f"{tea.replacement_cost_low:.0f} / {tea.replacement_cost_high:.0f} USD/MWh")
    _row("SOL wall fraction f_wall", f"{tea.f_wall:.2f}")
    _row("Blanket fluence allowable", f"{tea.allowable_blanket_fluence:.0f} MW·yr/m²")
    _row("Peak NWL", f"{tea.nwl_peak:.0f} MW/m²")
    _row("TF gap margin", f"{tea.gap_margin:.2f}")
    _row("TF packing factor", f"{tea.packing_factor:.1f}")
    _row("TF engineering margin", f"{tea.coil_margin_m:.1f}")

    print()

    # ===================================================================
    # KEY OUTPUTS — TWO-COLUMN TABLE
    # ===================================================================
    print("=" * 72)
    print("  KEY OUTPUTS")
    print("=" * 72)

    # Compute high-regulation building cost
    bldg_low = r.buildings.total_usd
    bldg_high = (r.buildings.nuclear_island_cost_usd * 2.2
                 + r.buildings.conventional_buildings_cost_usd)

    # Discounted energy
    cf_low = tea.capacity_factor
    cf_high = tea.capacity_factor * 0.8
    e_annual_low = si.p_net_mw * cf_low * 8760.0
    e_annual_high = si.p_net_mw * cf_high * 8760.0
    pv_energy_low = e_annual_low * r.annuity_factor
    pv_energy_high = e_annual_high * r.annuity_factor

    C1 = 28  # label width
    C2 = 18  # each value column

    hdr = f"  {'':─<{C1}}┬{'':─<{C2}}┬{'':─<{C2}}"
    sep = f"  {'':─<{C1}}┼{'':─<{C2}}┼{'':─<{C2}}"
    bot = f"  {'':─<{C1}}┴{'':─<{C2}}┴{'':─<{C2}}"

    def _shared(label: str, val: str):
        """Row where both scenarios share the same value (merged)."""
        pad = C2 * 2 + 1
        print(f"  {label:<{C1}}│{val:^{pad}}│")

    def _split(label: str, val_low: str, val_high: str):
        """Row with different values per scenario."""
        print(f"  {label:<{C1}}│{val_low:^{C2}}│{val_high:^{C2}}│")

    # Header
    print(f"\n  {'':─<{C1}}┬{'':─<{C2}}┬{'':─<{C2}}┐")
    _split("", COL_LOW, COL_HIGH)
    print(f"  {'':─<{C1}}┼{'':─<{C2}}┼{'':─<{C2}}┤")

    # Shared geometry / sizing
    _shared("R_major", f"{s.r_major_m:.2f} m")
    _shared("B_t (self-consistent)", f"{r.coils.b_t_self_consistent:.2f} T")
    _shared("FW thickness", f"{r.fw.thickness_m * 1000:.1f} mm")
    _shared("Blanket thickness", f"{r.blanket.total_thickness_m * 1000:.0f} mm")
    _shared("Shield/VV thickness", f"{r.shielding.shield_thickness_m * 1000:.0f} mm")
    _shared("TF coil thickness", f"{r.coils.delta_tf_total_m * 1000:.0f} mm")
    _shared("Replacement interval", f"{r.replacement_interval_yr:.1f} yr")
    _shared("Downtime / cycle", f"{r.required_replacement_time_months:.1f} months")

    print(f"  {'':─<{C1}}┼{'':─<{C2}}┼{'':─<{C2}}┤")

    # Split economics
    _split("Capacity factor", f"{cf_low:.0%}", f"{cf_high:.0%}")
    _split("CAPEX", fmt_usd(r.capex_low_usd), fmt_usd(r.capex_high_usd))
    _split("Replacement cost", fmt_usd(r.replacement_cost_low_usd),
           fmt_usd(r.replacement_cost_high_usd))
    _split("Energy", f"{pv_energy_low/1e6:,.1f} TWh", f"{pv_energy_high/1e6:,.1f} TWh")

    print(f"  {'':─<{C1}}┼{'':─<{C2}}┼{'':─<{C2}}┤")

    _split("LCOE", f"{r.lcoe_nominal_usd_mwh:.1f} USD/MWh",
           f"{r.lcoe_high_reg_usd_mwh:.1f} USD/MWh")

    print(f"  {'':─<{C1}}┴{'':─<{C2}}┴{'':─<{C2}}┘")
    print()


def _make_inputs_table_data(tea: TEAInputs):
    """Build cell data for the user-defined inputs table."""
    si = tea.sizing_inputs
    rows = [
        # (section_header, param, value)  — section_header=None for non-header rows
        ("Reactor Design", None, None),
        (None, "Net electric power", f"{si.p_net_mw:.0f} MW"),
        (None, "Engineering gain Q_eng", f"{si.q_eng:.1f}"),
        (None, "Aspect ratio A", f"{si.aspect:.1f}"),
        (None, "Elongation κ", f"{si.kappa:.2f}"),
        (None, "Triangularity δ", f"{si.triang:.2f}"),
        (None, "Fuel", si.fuel_type),
        (None, "B_t fraction of B_peak", f"{si.b_t_fraction:.2f}"),

        ("Physics Limits", None, None),
        (None, "q95 min", f"{si.q95_min:.1f}"),
        (None, "β_N max", f"{si.beta_n_max:.2f}"),
        (None, "H98y2 max", f"{si.h_max:.1f}"),
        (None, "f_GW max", f"{si.f_gw_max:.2f}"),

        ("Material Selections", None, None),
        (None, "Blanket type", si.blanket_type),
        (None, "Superconductor", si.sc_type),
        (None, "First wall material", tea.fw_material),
        (None, "Shield material", tea.shield_material),

        ("Efficiencies", None, None),
        (None, "η_thermal", f"{si.eta_thermal:.2f}"),
        (None, "η_wall_plug", f"{si.eta_wall_plug:.2f}"),
        (None, "η_absorption", f"{si.eta_absorption:.2f}"),

        ("TEA / Economics", None, None),
        (None, "Capacity factor", f"{tea.capacity_factor:.0%}"),
        (None, "Project lifespan", f"{tea.project_lifespan_yr:.0f} yr"),
        (None, "Discount rate", f"{tea.discount_rate:.0%}"),
        (None, "Indirect cost (low / high)", f"{tea.indirect_cost_frac_low:.0%} / {tea.indirect_cost_frac_high:.0%}"),
        (None, "Replacement cost (low / high)", f"{tea.replacement_cost_low:.0f} / {tea.replacement_cost_high:.0f} $/MWh"),
        (None, "SOL wall fraction f_wall", f"{tea.f_wall:.2f}"),
        (None, "Blanket fluence allowable", f"{tea.allowable_blanket_fluence:.0f} MW·yr/m²"),
        (None, "Peak NWL", f"{tea.nwl_peak:.0f} MW/m²"),
        (None, "TF gap margin", f"{tea.gap_margin:.2f}"),
        (None, "TF packing factor", f"{tea.packing_factor:.1f}"),
        (None, "TF engineering margin", f"{tea.coil_margin_m:.1f}"),
    ]
    return rows


def _make_outputs_table_data(r: TEAResult, tea: TEAInputs):
    """Build cell data for the key outputs table.

    Returns list of (label, low_val, high_val, is_shared) tuples.
    is_shared=True means the value is the same in both scenarios.
    """
    si = tea.sizing_inputs
    s = r.sizing

    bldg_low = r.buildings.total_usd
    bldg_high = (r.buildings.nuclear_island_cost_usd * 2.2
                 + r.buildings.conventional_buildings_cost_usd)
    direct_high = (r.fw.cost_usd + r.blanket.cost_usd + r.shielding.cost_usd
                   + r.coils.cost_usd + bldg_high
                   + r.turbine_cost_usd + r.bop_cost_usd)

    cf_low = tea.capacity_factor
    cf_high = tea.capacity_factor * 0.8
    pv_energy_low = si.p_net_mw * cf_low * 8760.0 * r.annuity_factor
    pv_energy_high = si.p_net_mw * cf_high * 8760.0 * r.annuity_factor

    rows = [
        ("R_major", f"{s.r_major_m:.2f} m", None, True),
        ("B_t (self-consistent)", f"{r.coils.b_t_self_consistent:.2f} T", None, True),
        ("FW thickness", f"{r.fw.thickness_m * 1000:.1f} mm", None, True),
        ("Blanket thickness", f"{r.blanket.total_thickness_m * 1000:.0f} mm", None, True),
        ("Shield/VV thickness", f"{r.shielding.shield_thickness_m * 1000:.0f} mm", None, True),
        ("TF coil thickness", f"{r.coils.delta_tf_total_m * 1000:.0f} mm", None, True),
        ("Replacement interval", f"{r.replacement_interval_yr:.1f} yr", None, True),
        ("Downtime / cycle", f"{r.required_replacement_time_months:.1f} months", None, True),
        (None, None, None, None),  # separator
        ("Capacity factor", f"{cf_low:.0%}", f"{cf_high:.0%}", False),
        ("CAPEX", fmt_usd(r.capex_low_usd), fmt_usd(r.capex_high_usd), False),
        ("Replacement cost", fmt_usd(r.replacement_cost_low_usd), fmt_usd(r.replacement_cost_high_usd), False),
        ("Energy", f"{pv_energy_low/1e6:,.1f} TWh", f"{pv_energy_high/1e6:,.1f} TWh", False),
        (None, None, None, None),  # separator
        ("LCOE", f"{r.lcoe_nominal_usd_mwh:.1f} USD/MWh", f"{r.lcoe_high_reg_usd_mwh:.1f} USD/MWh", False),
    ]
    return rows


def _draw_inputs_table(ax, tea: TEAInputs):
    """Render the user-defined inputs as a matplotlib table on ax."""
    ax.set_axis_off()
    rows = _make_inputs_table_data(tea)

    cell_text = []
    for section, param, value in rows:
        if section is not None:
            cell_text.append([section, ""])
        else:
            cell_text.append([param, value])

    table = ax.table(
        cellText=cell_text,
        colLabels=["Parameter", "Value"],
        colWidths=[0.65, 0.35],
        loc="upper center",
        cellLoc="left",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(8)
    table.scale(1.0, 1.15)

    # Style header
    for j in range(2):
        cell = table[0, j]
        cell.set_facecolor("#2c3e50")
        cell.set_text_props(color="white", fontweight="bold")

    # Style section headers and data rows
    row_idx = 1
    for section, param, value in rows:
        if section is not None:
            for j in range(2):
                cell = table[row_idx, j]
                cell.set_facecolor("#d5dbdb")
                cell.set_text_props(fontweight="bold")
        else:
            for j in range(2):
                cell = table[row_idx, j]
                cell.set_facecolor("#f9f9f9" if row_idx % 2 == 0 else "white")
        row_idx += 1

    ax.set_title("User-Defined Inputs", fontsize=11, fontweight="bold", pad=8)


def _draw_outputs_table(ax, r: TEAResult, tea: TEAInputs):
    """Render the key outputs two-column table on ax.

    Returns (table, shared_annotations) where shared_annotations is a
    list of (row_idx, value_text) for post-draw centered annotation.
    """
    ax.set_axis_off()
    rows = _make_outputs_table_data(r, tea)

    shared_annotations = []  # (table_row_idx, value_text)
    cell_text = []
    tbl_row = 1  # table row index (0 = header)
    for label, low, high, shared in rows:
        if label is None:
            cell_text.append(["", "", ""])
        elif shared:
            cell_text.append([label, "", ""])  # both value cells empty
            shared_annotations.append((tbl_row, low))
        else:
            cell_text.append([label, low, high])
        tbl_row += 1

    table = ax.table(
        cellText=cell_text,
        colLabels=["Output", COL_LOW, COL_HIGH],
        colWidths=[0.40, 0.30, 0.30],
        loc="upper center",
        cellLoc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(8)
    table.scale(1.0, 1.15)

    # Style header row
    for j in range(3):
        cell = table[0, j]
        cell.set_facecolor("#2c3e50")
        cell.set_text_props(color="white", fontweight="bold")

    # Style data rows
    row_idx = 1
    for label, low, high, shared in rows:
        if label is None:
            # Separator row — thin gray
            for j in range(3):
                cell = table[row_idx, j]
                cell.set_facecolor("#d5dbdb")
                cell.set_height(cell.get_height() * 0.4)
        elif shared:
            # Shared: merge visually by hiding the inner border
            table[row_idx, 0].set_text_props(ha="left")
            for j in range(3):
                table[row_idx, j].set_facecolor("#eaf2f8")
            table[row_idx, 1].visible_edges = "BLT"
            table[row_idx, 2].visible_edges = "BRT"
            # Text centering is handled post-draw via annotations
        else:
            table[row_idx, 0].set_text_props(ha="left")
            bg = "#f9f9f9" if row_idx % 2 == 0 else "white"
            for j in range(3):
                table[row_idx, j].set_facecolor(bg)

        # Bold the LCOE row
        if label == "LCOE":
            for j in range(3):
                table[row_idx, j].set_text_props(fontweight="bold")
                table[row_idx, j].set_facecolor("#d4efdf")

        row_idx += 1

    ax.set_title("Key Outputs", fontsize=11, fontweight="bold", pad=8)

    return table, shared_annotations


def plot_pie_charts(r: TEAResult, tea: TEAInputs, filename: str = "lcoe_breakdown.png"):
    """Generate pie charts + summary tables as a single PNG."""

    fig = plt.figure(figsize=(16, 20))
    gs = fig.add_gridspec(2, 2, height_ratios=[1, 1.4], hspace=0.25, wspace=0.3)

    # --- Row 1: Pie charts ---
    ax_pie1 = fig.add_subplot(gs[0, 0])
    ax_pie2 = fig.add_subplot(gs[0, 1])

    # Low LCOE pie
    labels_nom = []
    sizes_nom = []
    for k, v in r.cost_breakdown.items():
        if v > 0:
            labels_nom.append(k)
            sizes_nom.append(v)
    if sizes_nom:
        ax_pie1.pie(sizes_nom, labels=labels_nom, autopct="%1.1f%%", startangle=140)
    ax_pie1.set_title(f"{LABEL_LOW}\nLCOE = {r.lcoe_nominal_usd_mwh:.1f} USD/MWh",
                      fontsize=10, pad=12)

    # High LCOE pie
    buildings_reg = r.buildings.nuclear_island_cost_usd * 2.2 + r.buildings.conventional_buildings_cost_usd
    direct_reg = (r.fw.cost_usd + r.blanket.cost_usd + r.shielding.cost_usd
                  + r.coils.cost_usd + buildings_reg
                  + r.turbine_cost_usd + r.bop_cost_usd)
    indirect_reg = direct_reg * tea.indirect_cost_frac_high
    cost_breakdown_reg = {
        "First Wall": r.fw.cost_usd,
        "Blanket": r.blanket.cost_usd,
        "Shielding/VV": r.shielding.cost_usd,
        "TF Coils": r.coils.cost_usd,
        "Buildings (×2.2)": buildings_reg,
        "Turbine": r.turbine_cost_usd,
        "BoP": r.bop_cost_usd,
        "Indirect": indirect_reg,
        "Replacement": r.replacement_cost_high_usd,
    }
    labels_reg = []
    sizes_reg = []
    for k, v in cost_breakdown_reg.items():
        if v > 0:
            labels_reg.append(k)
            sizes_reg.append(v)
    if sizes_reg:
        ax_pie2.pie(sizes_reg, labels=labels_reg, autopct="%1.1f%%", startangle=140)
    ax_pie2.set_title(f"{LABEL_HIGH}\nLCOE = {r.lcoe_high_reg_usd_mwh:.1f} USD/MWh",
                      fontsize=10, pad=12)

    # --- Row 2: Tables (top-aligned) ---
    ax_tbl1 = fig.add_subplot(gs[1, 0])
    ax_tbl2 = fig.add_subplot(gs[1, 1])

    _draw_inputs_table(ax_tbl1, tea)
    out_table, shared_annotations = _draw_outputs_table(ax_tbl2, r, tea)

    # Top-align both table axes so shorter table aligns with taller one
    for ax_t in (ax_tbl1, ax_tbl2):
        ax_t.set_anchor("N")

    # Force layout so cell positions are computed
    fig.canvas.draw()

    # Center shared-row values across the merged col 1 + col 2 area
    for row_idx, value_text in shared_annotations:
        cell1 = out_table[row_idx, 1]
        cell2 = out_table[row_idx, 2]
        cx = cell1.get_x() + (cell1.get_width() + cell2.get_width()) / 2
        cy = cell1.get_y() + cell1.get_height() / 2
        ax_tbl2.text(cx, cy, value_text, ha="center", va="center",
                     fontsize=8, transform=ax_tbl2.transAxes)

    plt.savefig(filename, dpi=150, bbox_inches="tight", facecolor="white")
    print(f"  Pie chart saved to: {filename}")


def run_arc_tea():
    """ARC-like inputs with WCLL blanket for TEA demonstration."""

    sizing_inputs = SizingInputs(
        p_net_mw=190.0,
        q_eng=3.0,

        eta_thermal=0.40,
        eta_wall_plug=0.50,
        eta_absorption=0.90,

        blanket_type="WCLL",

        aspect=3.0,
        kappa=1.84,
        triang=0.33,

        sc_type="REBCO",
        b_t_fraction=0.93,
        fuel_type="DT",

        q95_min=7.2,
        beta_n_max=2.59,
        h_max=1.8,
        f_gw_max=0.67,

        t_i_range_kev=(10.0, 30.0),
    )

    tea_inputs = TEAInputs(sizing_inputs=sizing_inputs)

    result = calculate_lcoe(tea_inputs)
    print_result(result, tea_inputs)
    print_summary_tables(result, tea_inputs)
    plot_pie_charts(result, tea_inputs)


if __name__ == "__main__":
    run_arc_tea()
