# Copyright 2020
# Authors: Igor Andriyash
# License: GNU GPL v3
"""
Axiprop utils file

This file contains utility methods for Axiprop tool
"""
import numpy as np
from numba import njit, prange
from scipy.constants import c, e, m_e
from scipy.interpolate import interp1d

# try import numba and make dummy methods if it is not
try:
    from numba import njit, prange
    njit = njit(parallel=True, fastmath=True)
except Exception:
    prange = range
    def njit(func):
        def func_wrp(*args, **kw_args):
            print(f"Install Numba to get `{func.__name__}` " + \
                   "function greatly accelerated")
            return func(*args, **kw_args)
        return func_wrp

def laser_from_fu(fu, kz, r, normalize=False):
    """
    Generate array with spectra-radial field
    distribution with the pre-defined function
    """

    fu = njit(fu)

    a0 = fu( ( kz * np.ones((*kz.shape, *r.shape)).T ).T,
             r[None,:] * np.ones((*kz.shape, *r.shape)) )

    if normalize:
        a0 /= (np.abs(a0)**2).sum(0).max()**0.5

    return a0

def mirror_parabolic(f0, kz, r):
    """
    Generate array with spectra-radial phase
    representing the on-axis Parabolic Mirror
    """
    s_ax = r**2/4/f0

    val = np.exp(   2j * s_ax[None,:] * \
                 ( kz * np.ones((*kz.shape, *r.shape)).T ).T)
    return val

@njit
def get_temporal_1d(u, u_t, t, kz, Nr_loc):
    """
    Resonstruct temporal-radial field distribution
    """
    Nkz, Nr = u.shape
    Nt = t.size

    assert u_t.shape[-1] == Nr

    for it in prange(Nt):
        FFT_factor = np.exp(1j * kz * c * t[it])
        for ir in range(Nr_loc):
            u_t[it] += np.real(u[:,ir] * FFT_factor).sum()

    return u_t

@njit
def get_temporal_radial(u, u_t, t, kz):
    """
    Resonstruct temporal-radial field distribution
    """
    Nkz, Nr = u.shape
    Nt = t.size

    assert u_t.shape[-1] == Nr
    assert u_t.shape[0] == Nt

    for it in prange(Nt):
        FFT_factor = np.exp(1j * kz * c * t[it])
        for ir in range(Nr):
            u_t[it, ir] = np.real(u[:, ir] * FFT_factor).sum()
    return u_t

@njit
def get_temporal_slice2d(u, u_t, t, kz):
    """
    Resonstruct temporal-radial field distribution
    """
    Nkz, Nx, Ny = u.shape
    Nt = t.size

    assert u_t.shape[-1] == Nx

    for it in prange(Nt):
        FFT_factor = np.exp(1j * kz * c * t[it])
        for ix in range(Nx):
            u_t[it, ix] = np.real(u[:, ix, Ny//2-1] * FFT_factor).sum()
    return u_t

@njit
def get_temporal_3d(u, t, kz):
    """
    Resonstruct temporal-radial field distribution
    """
    Nkz, Nx, Ny = u.shape
    Nt = t.size

    u_t = np.empty((Nt, Nx, Ny))

    for it in prange(Nt):
        FFT_factor = np.exp(1j * kz * c * t[it])
        for ix in range(Nx):
            for iy in range(Ny):
                u_t[it, ix, iy] = np.real(u[:, ix, iy] * FFT_factor).sum()

    return u_t



#### FBPIC profile
@njit
def get_E_r(t, u, kz):
    FFT_factor = (np.exp(1j * kz * c * t) * np.ones_like(u).T).T
    u_r = np.real(u * FFT_factor).sum(0) / FFT_factor.size
    return u_r


class LaserProfile( object ):

    def __init__( self, propagation_direction, gpu_capable=False ):
        assert propagation_direction in [-1, 1]
        self.propag_direction = float(propagation_direction)
        self.gpu_capable = gpu_capable

class AxipropLaser( LaserProfile ):

    def __init__( self, a0, u, kz, r, time_offset=0.0,
                  theta_pol=0., lambda0=0.8e-6 ):

        LaserProfile.__init__(self, propagation_direction=1, gpu_capable=False)

        k0 = 2*np.pi/lambda0
        E0 = a0*m_e*c**2*k0/e

        self.u = u
        self.kz = kz
        self.r = r
        self.time_offset = time_offset

        self.E0x = E0 * np.cos(theta_pol)
        self.E0y = E0 * np.sin(theta_pol)

    def E_field( self, x, y, z, t ):
        u_r = get_E_r( t + self.time_offset, self.u, self.kz)
        r_p = np.sqrt(x*x + y*y)
        fu = interp1d(self.r, u_r,  kind='cubic',
                      fill_value=0.0, bounds_error=False )
        profile = fu(r_p)
        Ex = self.E0x * profile
        Ey = self.E0y * profile
        return( Ex.real, Ey.real )


######## WARPX [WIP]

"""
The following methods are taken from the WarpX examples
https://github.com/ECP-WarpX/WarpX/tree/development/Examples/Modules/laser_injection_from_file
and all rights belong to WarpX development group Copyright (c) 2018
"""

def write_file_unf(fname, x, y, t, E):
    """ For a given filename fname, space coordinates x and y, time coordinate t
    and field E, write a WarpX-compatible input binary file containing the
    profile of the laser pulse. This function should be used in the case
    of a uniform spatio-temporal mesh
    """

    with open(fname, 'wb') as file:
        flag_unif = 1
        file.write(flag_unif.to_bytes(1, byteorder='little'))
        file.write((len(t)).to_bytes(4, byteorder='little', signed=False))
        file.write((len(x)).to_bytes(4, byteorder='little', signed=False))
        file.write((len(y)).to_bytes(4, byteorder='little', signed=False))
        file.write(t[0].tobytes())
        file.write(t[-1].tobytes())
        file.write(x[0].tobytes())
        file.write(x[-1].tobytes())
        if len(y) == 1 :
            file.write(y[0].tobytes())
        else :
            file.write(y[0].tobytes())
            file.write(y[-1].tobytes())
        file.write(E.tobytes())


def write_file(fname, x, y, t, E):
    """ For a given filename fname, space coordinates x and y, time coordinate t
    and field E, write a WarpX-compatible input binary file containing the
    profile of the laser pulse
    """

    with open(fname, 'wb') as file:
        flag_unif = 0
        file.write(flag_unif.to_bytes(1, byteorder='little'))
        file.write((len(t)).to_bytes(4, byteorder='little', signed=False))
        file.write((len(x)).to_bytes(4, byteorder='little', signed=False))
        file.write((len(y)).to_bytes(4, byteorder='little', signed=False))
        file.write(t.tobytes())
        file.write(x.tobytes())
        file.write(y.tobytes())
        file.write(E.tobytes())