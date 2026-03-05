"""Bosch-Hale fusion reaction rate parametrization.

Reference:
    H.-S. Bosch and G. M. Hale, Nuclear Fusion 32(4), 1992.
"""

from dataclasses import dataclass

import numpy as np


REACTION_CONSTANTS_DT = {
    "bg": 34.3827,
    "mrc2": 1.124656e6,
    "cc1": 1.17302e-9,
    "cc2": 1.51361e-2,
    "cc3": 7.51886e-2,
    "cc4": 4.60643e-3,
    "cc5": 1.35000e-2,
    "cc6": -1.06750e-4,
    "cc7": 1.36600e-5,
}

REACTION_CONSTANTS_DHE3 = {
    "bg": 68.7508,
    "mrc2": 1.124572e6,
    "cc1": 5.51036e-10,
    "cc2": 6.41918e-3,
    "cc3": -2.02896e-3,
    "cc4": -1.91080e-5,
    "cc5": 1.35776e-4,
    "cc6": 0.0,
    "cc7": 0.0,
}

REACTION_CONSTANTS_DD1 = {
    "bg": 31.3970,
    "mrc2": 0.937814e6,
    "cc1": 5.43360e-12,
    "cc2": 5.85778e-3,
    "cc3": 7.68222e-3,
    "cc4": 0.0,
    "cc5": -2.96400e-6,
    "cc6": 0.0,
    "cc7": 0.0,
}

REACTION_CONSTANTS_DD2 = {
    "bg": 31.3970,
    "mrc2": 0.937814e6,
    "cc1": 5.65718e-12,
    "cc2": 3.41267e-3,
    "cc3": 1.99167e-3,
    "cc4": 0.0,
    "cc5": 1.05060e-5,
    "cc6": 0.0,
    "cc7": 0.0,
}


@dataclass
class BoschHaleConstants:
    """Constants for the Bosch-Hale reactivity calculation."""

    bg: float
    mrc2: float
    cc1: float
    cc2: float
    cc3: float
    cc4: float
    cc5: float
    cc6: float
    cc7: float


def bosch_hale_reactivity(
    ion_temperature_profile: np.ndarray, reaction_constants: BoschHaleConstants
) -> np.ndarray:
    """Volumetric fusion reaction rate <sigmav> [m^3/s].

    Valid range: 0.2 < T < 100 keV (D-T, D-D) or 0.5 < T < 190 keV (D-3He).

    Parameters:
        ion_temperature_profile: Ion temperature [keV].
        reaction_constants: Bosch-Hale fit coefficients.

    Returns:
        Reactivity <sigmav> [m^3/s] at each temperature point.
    """
    theta1 = (
        ion_temperature_profile
        * (
            reaction_constants.cc2
            + ion_temperature_profile
            * (reaction_constants.cc4 + ion_temperature_profile * reaction_constants.cc6)
        )
        / (
            1.0
            + ion_temperature_profile
            * (
                reaction_constants.cc3
                + ion_temperature_profile
                * (
                    reaction_constants.cc5
                    + ion_temperature_profile * reaction_constants.cc7
                )
            )
        )
    )
    theta = ion_temperature_profile / (1.0 - theta1)

    xi = ((reaction_constants.bg**2) / (4.0 * theta)) ** (1 / 3)

    sigmav = (
        1.0e-6
        * reaction_constants.cc1
        * theta
        * np.sqrt(xi / (reaction_constants.mrc2 * ion_temperature_profile**3))
        * np.exp(-3.0 * xi)
    )

    t_mask = ion_temperature_profile == 0.0
    sigmav[t_mask] = 0.0

    return sigmav
