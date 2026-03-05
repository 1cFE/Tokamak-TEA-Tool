"""Building cost model — Araiinejad (2024/2025) NCET/EEDB methodology.

Wraps fusion_buildings_cost.structures_cost() into the TEA interface.

See fusion_buildings_cost.py for full methodology documentation.
"""

from dataclasses import dataclass

from tokamak_sizing.sizing import SizingResult, SizingInputs
from tokamak_sizing.fusion_buildings_cost import structures_cost


@dataclass
class BuildingsCostResult:
    """Building cost breakdown."""
    nuclear_island_cost_usd: float
    conventional_buildings_cost_usd: float
    total_usd: float
    cost_per_kw: float
    volume_ratio: float


def calculate_buildings(
    sizing: SizingResult,
    inputs: SizingInputs,
    *,
    high_regulation_mode: bool = False,
) -> BuildingsCostResult:
    """Calculate building costs using Araiinejad NCET/EEDB methodology.

    Parameters
    ----------
    sizing : SizingResult
        Reactor sizing output (provides geometry).
    inputs : SizingInputs
        Sizing inputs (provides P_net, aspect ratio, kappa).
    high_regulation_mode : bool
        If True, uses 'upper' regulatory bound (fission-like, no 1/2.2 discount).
        If False, uses 'lower' bound (fusion regulatory discount).
    """
    r0 = sizing.r_major_m
    a = r0 / inputs.aspect
    kappa = inputs.kappa
    p_net = inputs.p_net_mw

    regulatory = "upper" if high_regulation_mode else "lower"

    result = structures_cost(
        P_e_net=p_net,
        R0=r0,
        a=a,
        kappa=kappa,
        regulatory=regulatory,
    )

    return BuildingsCostResult(
        nuclear_island_cost_usd=result.nuclear_buildings_M * 1e6,
        conventional_buildings_cost_usd=result.conventional_buildings_M * 1e6,
        total_usd=result.total_structures_M * 1e6,
        cost_per_kw=result.total_structures_per_kW,
        volume_ratio=result.volume_ratio,
    )
