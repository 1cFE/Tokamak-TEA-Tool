# Tokamak TEA Tool

Sizes a D-T tokamak fusion power plant and computes the Levelized Cost of Electricity (LCOE) across low- and high-regulation scenarios.

## Quick Start

```bash
# Install
pip install -e .

# Run the ARC-like demo case
python -m tokamak_sizing.tea_runner
```

This prints a full cost breakdown to the terminal and saves `lcoe_breakdown.png` with pie charts and summary tables.

## Usage

### TEA / LCOE Calculator

```python
from tokamak_sizing.sizing import SizingInputs
from tokamak_sizing.tea import TEAInputs, calculate_lcoe

sizing = SizingInputs(
    p_net_mw=190.0,         # Target net electric power [MW]
    q_eng=3.0,              # Engineering gain P_gross/P_recirc
    eta_thermal=0.40,       # Thermal-to-electric efficiency
    eta_wall_plug=0.50,     # HCD wall-plug efficiency
    eta_absorption=0.90,    # Plasma heating absorption
    blanket_type="WCLL",    # Blanket concept
    aspect=3.0,             # Aspect ratio R/a
    kappa=1.84,             # Plasma elongation
    triang=0.33,            # Triangularity
    sc_type="REBCO",        # Superconductor type
    b_t_fraction=0.93,      # Operating fraction of max B_t
    fuel_type="DT",
    q95_min=7.2,
    beta_n_max=2.59,
    h_max=1.8,
    f_gw_max=0.67,
)

tea = TEAInputs(sizing_inputs=sizing)
result = calculate_lcoe(tea)

print(f"LCOE (low):  {result.lcoe_nominal_usd_mwh:.1f} USD/MWh")
print(f"LCOE (high): {result.lcoe_high_reg_usd_mwh:.1f} USD/MWh")
```

Material properties (first wall, blanket, shield, TF coils) are auto-resolved from the high-level selections (`blanket_type`, `sc_type`, `shield_material`). Override any property by passing it explicitly to `TEAInputs`.

### Reactor Sizing Only

```python
from tokamak_sizing.sizing import SizingInputs, TokamakSizeOptimizatIonTool

result = TokamakSizeOptimizatIonTool(SizingInputs(p_net_mw=500, q_eng=3.0))
print(f"R_major = {result.r_major_m:.2f} m, P_fusion = {result.p_fusion_mw:.0f} MW")
```

### Key Input Parameters

| Category | Parameter | Default | Description |
|----------|-----------|---------|-------------|
| **Power** | `p_net_mw` | *(required)* | Net electric output [MW] |
| | `q_eng` | *(required)* | Engineering gain |
| **Materials** | `blanket_type` | `"HCPB"` | Blanket concept (`WCLL`, `HCPB`, `DCLL`, `FLiBe`, `LiPb`) |
| | `sc_type` | `"Nb3Sn"` | Superconductor (`REBCO`, `Nb3Sn`, `NbTi`) |
| | `shield_material` | `"SS316"` | Shield material (`SS316`, `WC`) |
| **Geometry** | `aspect` | `3.1` | Aspect ratio R/a |
| | `kappa` | `1.65` | Elongation |
| | `triang` | `0.33` | Triangularity |
| **Economics** | `capacity_factor` | `0.85` | Plant availability |
| | `discount_rate` | `0.08` | Annual discount rate |
| | `project_lifespan_yr` | `30` | Plant lifetime [yr] |
| | `turbine_cost_per_kw` | `267` | Turbine equipment [USD/kW_gross] |
| | `bop_cost_per_kw` | `197` | Balance of plant [USD/kW_gross] |

## How It Works

### 1. Reactor Sizing

The sizing module (`sizing.py`) uses an **outside-in** approach:

1. **Top-down power balance** — From `P_net` and `Q_eng`, derive `P_gross`, `P_recirc`, `P_thermal`, and `P_fusion`.
2. **Temperature sweep** — For each candidate ion temperature T_i, compute the DT reactivity (Bosch-Hale parameterization), then find the minimum major radius `R_major` that satisfies all constraints simultaneously:
   - **Greenwald density limit** — `n_e < f_GW * n_GW`
   - **Troyon beta limit** — `beta_N < beta_N_max`
   - **Kink safety factor** — `q_95 > q_95_min`
   - **Energy confinement** — `H_98y2 < H_max` (IPB98(y,2) scaling)
   - **Neutron wall load** — `P_nw < P_nw_max`
   - **Divertor heat exhaust** — `P_sep/R < P_sep_R_max`
3. **Select optimum** — The T_i giving the smallest feasible R_major is chosen.

### 2. Component Costing

Each subsystem is costed from the sized geometry:

| Component | Method |
|-----------|--------|
| **First wall** | Thermal thickness from heat flux (q = k*ΔT/t), capped at 5 mm; mass × fabricated material cost |
| **Blanket** | Breeding zone from TBR requirement + structural overhead; volume × avg density × cost/kg |
| **Shield / VV** | Exponential neutron attenuation to meet SC fluence limit; mass × cost/kg |
| **TF coils** | Iterative solve for winding pack + structural thickness (Lorentz hoop stress); cost = NI × length × cost/kA·m |
| **Buildings** | Araiinejad NCET/EEDB methodology: PWR12 baseline scaled by (P_e/1200)^0.6, reactor building adjusted by torus volume ratio vs ITER |
| **Turbine** | Flat rate: 267 USD/kW × P_gross (pyFECONS) |
| **BoP** | Flat rate: 197 USD/kW × P_gross (pyFECONS) |

### 3. LCOE Calculation

```
LCOE = (CAPEX + PV_replacement) / PV_energy
```

Where:
- **Direct cost** = sum of all component costs
- **Indirect cost** = 19% (low) or 38% (high) of direct cost
- **CAPEX** = direct + indirect
- **Replacement cost** = present value of periodic blanket replacements at 11 (low) or 107 (high) USD/MWh, discounted at each replacement interval
- **Energy** = P_net × CF × 8760 × annuity factor

Two scenarios are computed:

| | Low LCOE | High LCOE |
|--|----------|-----------|
| Indirect cost | 19% | 38% |
| Replacement rate | 11 USD/MWh | 107 USD/MWh |
| Building regulation | Fusion discount (÷2.2) | Fission-like (×1.0) |
| Capacity factor | 85% | 68% (85% × 0.8) |

### 4. Material Databases

Material properties are stored in `materials.py` and auto-resolved from high-level selections:

- **Blanket type** → FW material, coolant temperature, blanket density/cost
- **SC type** → fluence limit, winding pack current density, conductor cost
- **Shield material** → attenuation cross-section, density, cost

Any auto-resolved property can be overridden by passing it explicitly to `TEAInputs`.

## Project Structure

```
tokamak_sizing/
    sizing.py              # Outside-in reactor sizing engine
    tea.py                 # TEA inputs/outputs and LCOE calculation
    tea_runner.py          # Demo entry point, terminal output, PNG generation
    component_costs.py     # FW, blanket, and shielding cost models
    coil_costs.py          # TF coil iterative design and cost
    buildings_cost.py      # Account 21 wrapper
    fusion_buildings_cost.py  # Araiinejad NCET/EEDB building cost model
    materials.py           # Material property lookup databases
    sizing.py              # Core reactor sizing
    constants.py           # Physical constants
    confinement_time.py    # IPB98(y,2) energy confinement scaling
    fusion_reactions.py    # Bosch-Hale DT/DHe3/DD reactivity
    plasma_geometry.py     # Sauter elongation/triangularity geometry
    sizing_runner.py       # Sizing-only demo with validation cases
```

## References

- Araiinejad et al., "Levelized cost of electricity for a fusion power plant" (2024/2025)
- Stewart & Shirvan, "Capital cost estimation for advanced nuclear power plants" (2022)
- Federici et al., "Overview of the DEMO staged design approach" (2019)
- Bosch & Hale, "Improved formulas for fusion cross-sections and thermal reactivities" (1992)
- ITER Physics Basis, Ch. 2: Plasma confinement and transport (1999)
