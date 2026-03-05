"""Plasma geometry calculations (Sauter model).

Reference:
    O. Sauter, Fusion Engineering and Design 112, pp. 633-645, 2016.
"""

import numpy as np


def sauter_geometry(
    a: float, r0: float, kappa: float, triang: float, square: float
) -> tuple[float, float, float, float]:
    """Plasma geometry parameters using the Sauter model.

    Parameters:
        a: Plasma minor radius [m]
        r0: Plasma major radius [m]
        kappa: Plasma separatrix elongation
        triang: Plasma separatrix triangularity
        square: Plasma squareness

    Returns:
        (poloidal_perimeter, surface_area, cross_section_area, volume)
    """
    w07 = square + 1
    eps = a / r0

    len_plasma_poloidal = (
        2.0e0
        * np.pi
        * a
        * (1 + 0.55 * (kappa - 1))
        * (1 + 0.08 * triang**2)
        * (1 + 0.2 * (w07 - 1))
    )

    a_plasma_surface = (
        2.0e0 * np.pi * r0 * (1 - 0.32 * triang * eps) * len_plasma_poloidal
    )

    a_plasma_poloidal = np.pi * a**2 * kappa * (1 + 0.52 * (w07 - 1))

    vol_plasma = 2.0e0 * np.pi * r0 * (1 - 0.25 * triang * eps) * a_plasma_poloidal

    return (
        len_plasma_poloidal,
        a_plasma_surface,
        a_plasma_poloidal,
        vol_plasma,
    )
