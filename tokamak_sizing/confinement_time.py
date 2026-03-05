"""Energy confinement time scalings for tokamak plasmas."""


def iter_ipb98y2_confinement_time(
    pcur: float,
    b_plasma_toroidal_on_axis: float,
    dnla19: float,
    p_plasma_loss_mw: float,
    rmajor: float,
    kappa_ipb: float,
    aspect: float,
    afuel: float,
) -> float:
    """IPB98(y,2) ELMy H-mode scaling confinement time [s].

    Parameters:
        pcur: Plasma current [MA]
        b_plasma_toroidal_on_axis: Toroidal magnetic field [T]
        dnla19: Line averaged electron density [10^19 m^-3]
        p_plasma_loss_mw: Net heating power [MW]
        rmajor: Plasma major radius [m]
        kappa_ipb: IPB plasma separatrix elongation
        aspect: Aspect ratio
        afuel: Fuel atomic mass number

    References:
        - ITER Physics Expert Groups, Nuclear Fusion 39(12), 1999.
        - Kardaun et al., Nuclear Fusion 48(9), 2008 (corrections).
    """
    return (
        0.0562e0
        * pcur**0.93e0
        * b_plasma_toroidal_on_axis**0.15e0
        * dnla19**0.41e0
        * p_plasma_loss_mw ** (-0.69e0)
        * rmajor**1.97e0
        * kappa_ipb**0.78e0
        * aspect ** (-0.58e0)
        * afuel**0.19e0
    )
