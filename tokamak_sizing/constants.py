"""Physical constants for fusion reactor sizing.

Subset of PROCESS constants.py — only the constants needed by the sizing tool.
All values from NIST with references preserved.
"""

ELECTRON_CHARGE = 1.602176634e-19
"""Electron / elementary charge [C]
Reference: National Institute of Standards and Technology (NIST)
https://physics.nist.gov/cgi-bin/cuu/Value?e|search_for=electron+charge
"""

ELECTRON_VOLT = ELECTRON_CHARGE
"""Electron volt [J]"""

KILOELECTRON_VOLT = ELECTRON_VOLT * 1e3
"""Kiloelectron volt [J]"""

PROTON_MASS = 1.67262192595e-27
"""Proton mass [kg]
Reference: NIST https://physics.nist.gov/cgi-bin/cuu/Value?mp
"""

DEUTERON_MASS = 3.3435837768e-27
"""Deuteron mass [kg]
Reference: NIST https://physics.nist.gov/cgi-bin/cuu/Value?md
"""

TRITON_MASS = 5.0073567512e-27
"""Triton mass [kg]
Reference: NIST https://physics.nist.gov/cgi-bin/cuu/Value?mt
"""

NEUTRON_MASS = 1.67492750056e-27
"""Neutron mass [kg]
Reference: NIST https://physics.nist.gov/cgi-bin/cuu/Value?mn
"""

ALPHA_MASS = 6.6446573450e-27
"""Alpha particle mass [kg]
Reference: NIST https://physics.nist.gov/cgi-bin/cuu/Value?mal
"""

HELION_MASS = 5.0064127862e-27
"""Helion (3He) mass [kg]
Reference: NIST https://physics.nist.gov/cgi-bin/cuu/Value?mh
"""

SPEED_LIGHT = 299792458.0
"""Speed of light in vacuum [m/s]
Reference: NIST https://physics.nist.gov/cgi-bin/cuu/Value?c
"""

# Derived fusion reaction energies (mass defect × c²)

D_T_ENERGY = (
    (DEUTERON_MASS + TRITON_MASS) - (ALPHA_MASS + NEUTRON_MASS)
) * SPEED_LIGHT**2
"""Deuterium-Tritium reaction energy [J]"""

D_HELIUM_ENERGY = (
    (DEUTERON_MASS + HELION_MASS) - (ALPHA_MASS + PROTON_MASS)
) * SPEED_LIGHT**2
"""Deuterium-Helion (3He) reaction energy [J]"""

# Energy fractions (centre-of-mass, non-relativistic)

DT_NEUTRON_ENERGY_FRACTION = ALPHA_MASS / (NEUTRON_MASS + ALPHA_MASS)
"""D-T energy fraction carried by neutron (~79.9%)"""

DHELIUM_PROTON_ENERGY_FRACTION = ALPHA_MASS / (PROTON_MASS + ALPHA_MASS)
"""D-3He energy fraction carried by proton (~79.9%)"""

# Electromagnetic

RMU0 = 1.256637062e-6
"""Permeability of free space [H/m]"""
