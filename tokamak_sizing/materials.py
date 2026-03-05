"""Material property databases for TEA component cost calculations.

Each dictionary maps a material/type name to the properties needed by
the corresponding cost function.  TEAInputs.__post_init__ resolves
these lookups automatically; users can override individual properties
by passing non-None values.

Sources noted inline.  LTS values marked (approximate) reflect
community estimates, not firm vendor quotes.
"""

# ---------------------------------------------------------------------------
# First wall materials
# ---------------------------------------------------------------------------

FW_MATERIALS = {
    "W": {
        "t_max_k": 1473.0,         # 1200 °C, recrystallization limit
        "k_w_mk": 170.0,           # Thermal conductivity [W/m/K] at ~800 °C
        "rho": 19300.0,             # Density [kg/m³]
        "cost_per_kg": 150.0,      # Fabricated PFC-grade W [USD/kg] (Federici 2019)
    },
}

# Blanket type → default FW material
BLANKET_FW_DEFAULTS = {
    "WCLL":  "W",
    "HCPB":  "W",
    "DCLL":  "W",
    "FLiBe": "W",
    "LiPb":  "W",
}

# Blanket type → FW coolant temperature [K]
BLANKET_COOLANT_TEMP_K = {
    "WCLL":  673.0,     # Water-cooled, ~400 °C
    "HCPB":  773.0,     # He-cooled, ~500 °C
    "DCLL":  773.0,     # He-cooled FW circuit, ~500 °C
    "FLiBe": 873.0,     # Molten salt, ~600 °C
    "LiPb":  673.0,     # LiPb, ~400 °C
}


# ---------------------------------------------------------------------------
# Blanket TEA parameters (density and cost — NOT in sizing.py's BLANKET_PARAMS)
# ---------------------------------------------------------------------------

BLANKET_TEA_PARAMS = {
    "WCLL": {
        "rho_avg": 7770.0,     # ~60% PbLi + ~25% EUROFER + ~15% void [kg/m³]
        "cost_per_kg": 200.0,  # Bachmann et al. (2024) WCLL module cost [USD/kg]
    },
    "HCPB": {
        "rho_avg": 4200.0,     # Pebble bed + EUROFER structure (approximate)
        "cost_per_kg": 250.0,  # Ceramic pebble modules (approximate)
    },
    "DCLL": {
        "rho_avg": 6800.0,     # PbLi + SiC inserts + EUROFER (approximate)
        "cost_per_kg": 300.0,  # SiC flow channel inserts (approximate)
    },
    "FLiBe": {
        "rho_avg": 2500.0,     # FLiBe (~1940) + Inconel structure (approximate)
        "cost_per_kg": 350.0,  # Molten salt tank + Inconel fabrication (approximate)
    },
    "LiPb": {
        "rho_avg": 7200.0,     # PbLi + steel structure (approximate)
        "cost_per_kg": 180.0,  # Simpler than WCLL (approximate)
    },
}


# ---------------------------------------------------------------------------
# Shield materials
# ---------------------------------------------------------------------------

SHIELD_MATERIALS = {
    "SS316": {
        "sigma_r_cm": 0.096,       # Macroscopic removal cross-section [1/cm]
        "rho": 7800.0,             # Density [kg/m³]
        "cost_per_kg": 30.0,       # Fabricated nuclear-grade SS316 [USD/kg]
    },
    "WC": {
        "sigma_r_cm": 0.145,       # Tungsten carbide — higher attenuation
        "rho": 15630.0,            # Density [kg/m³]
        "cost_per_kg": 120.0,      # Fabricated WC [USD/kg]
    },
}


# ---------------------------------------------------------------------------
# Superconductor → fluence limit at the TF coil [n/m²]
# ---------------------------------------------------------------------------

SC_FLUENCE_LIMITS = {
    "REBCO":  1e22,     # HTS, radiation-tolerant at 20–30 K
    "Nb3Sn":  1e19,     # LTS, radiation-sensitive at 4 K (approximate)
    "NbTi":   1e18,     # LTS, most radiation-sensitive at 4 K (approximate)
}


# ---------------------------------------------------------------------------
# Superconductor → coil TEA parameters (winding pack J + cost)
# ---------------------------------------------------------------------------

SC_COIL_PARAMS = {
    "REBCO": {
        "j_wp_a_mm2": 150.0,       # Winding pack current density [A/mm²]
        "cost_per_kam": 30.0,       # NOAK REBCO [USD/kA·m] (Araiinejad)
    },
    "Nb3Sn": {
        "j_wp_a_mm2": 40.0,        # ITER-class winding pack J (approximate)
        "cost_per_kam": 8.0,        # NOAK Nb3Sn [USD/kA·m] (approximate)
    },
    "NbTi": {
        "j_wp_a_mm2": 25.0,        # Low-field NbTi winding pack J (approximate)
        "cost_per_kam": 5.0,        # NOAK NbTi [USD/kA·m] (approximate)
    },
}
