import numpy as np

def galaxy_psf_convolution(re, e1, e2, profile,
                           cdmatrix, dx, dy, psfimage,
                           debug=False):
    '''
    Perform the Fourier-space convolution of a parametric galaxy
    profile by a pixelized PSF model.

    re: float, effective radius in arcsec
    e1: float (-1,1): ellipticity component
    e2: float (-1,1): ellipticity component
    profile: object with "amp" and "var" terms, eg ExpGalaxy, DevGalaxy,
       or GaussianGalaxy, mixture-of-Gaussian representations of galaxy
       profile.
    cdmatrix: 2x2 numpy array, [[CD1_1, CD1_2],[CD2_1, CD2_2]] of local
       astrometric transformation
    dx: subpixel shift in x
    dy: subpixel shift in y
    psfimage: numpy array (image) of the PSF
    debug: return intermediate values, for debugging?

    Return:
    PSF-convolved galaxy profile as numpy image the same size as the psfimage.

    OR tuple of stuff (see below) if debug=True.
    
    '''
    # Compute galaxy affine transform terms
    # eqn (2)
    e = np.hypot(e1, e2)
    orig_e = e
    # add this max() to handle e1=e2=0.
    e = max(e, 1e-16)
    # eqn (A9)
    # c2 = cos^2 theta
    c2 = 0.5 * (1 + e1/e)
    # eqn (A10)
    # s2 = sin^2 theta
    s2 = 0.5 * (1 - e1/e)
    # eqn (A11)
    # cs = cos theta * sin theta
    cs = 0.5 * e2/e
    # Axis ratio minor/major
    # eqn (3)
    a = (1 - e) / (1 + e)
    if orig_e == 0:
        a = 1.
    
    # CD matrix term shortcuts
    # eqn (A6)
    t = cdmatrix[0, 0]
    u = cdmatrix[0, 1]
    v = cdmatrix[1, 0]
    w = cdmatrix[1, 1]
    # eqn (A2) -- pixel scale factor
    f = (re / 3600. / (t*w-u*v))**2
    
    # Galaxy * WCS covariance matrix terms
    # eqn (A3)
    c11 = (a**2 * (w**2*c2 + 2*u*w*cs + u**2*s2)
           + w**2*s2 - 2*u*w*cs + u**2*c2)
    # eqn (A4)
    c12 = (-a**2 * (v*w*c2 + u*v*cs + t*w*cs + t*u*s2)
           - v*w*s2 + u*v*cs + t*w*cs - t*u*c2)
    # eqn (A5)
    c22 = (a**2 * (v**2*c2 + 2*t*v*cs + t**2*s2)
           + t**2*c2 - 2*t*v*cs + v**2*s2)

    # Compute Fourier transform of PSF, recording the frequencies v,w
    P = np.fft.rfft2(psfimage)
    pH,pW = psfimage.shape
    v = np.fft.rfftfreq(pW)
    w = np.fft.fftfreq(pH)
    
    # precompute the inner arg of the galaxy's Fourier transform
    ee = (-2. * np.pi**2 * f *
            (  c11 * v[np.newaxis,:]**2 +
               c22 * w[:,np.newaxis]**2 +
             2*c12 * v[np.newaxis,:]*w[:,np.newaxis]))

    # compute the Fourier transform of the galaxy
    Fgal = np.zeros((len(w), len(v)), np.complex128)
    for amp,var in zip(profile.amp, profile.var):
        Fgal += amp * np.exp(ee * var)

    # shift by dx,dy
    if dx != 0 or dy != 0:
        Fgal *= np.exp(-2. * np.pi * 1j * (dx*v[np.newaxis,:] +
                                           dy*w[:,np.newaxis]))

    # multiply in Fourier space and inverse-transform
    G = np.fft.irfft2(Fgal * P, s=(pH,pW))

    if debug:
        return P, Fgal, G, v, w

    return G
    
    

class ExpGalaxy(object):
    # magic arrays, generated by running optimize_mixture_profiles.py
    # in David Hogg's "TheTractor" github repository:
    # http://github.com/davidwhogg/TheTractor
    amp = np.array([  1.99485977e-04,   2.61612679e-03,   1.89726655e-02,
                      1.00186544e-01,   3.68534484e-01,   5.09490694e-01])
    var = np.array([  1.20078965e-03,   8.84526493e-03,   3.91463084e-02,
                      1.39976817e-01,   4.60962500e-01,   1.50159566e+00])


class DevGalaxy(object):
    amp = np.array([ 0.00201838,  0.01136789,  0.03247163,  0.07192882,
                     0.13427227,  0.21136265,  0.27099981,  0.26557856])
    var = np.array([  2.23759216e-04,   1.00220099e-03,   4.18731126e-03,
                      1.69432589e-02,   6.84850479e-02,   2.87207080e-01,
                      1.33320254e+00,   8.40215071e+00])

class GaussianGalaxy(object):
    amp = np.array([1.])
    var = np.array([1.])


if __name__ == '__main__':
    import matplotlib
    matplotlib.use('Agg')
    import pylab as plt

    # PSF (and convolved galaxy) image size
    ph,pw = 64,64
    xx,yy = np.meshgrid(np.arange(pw), np.arange(ph))
    cx1,cy1 = 28,28
    co = 0.7
    # Create a weird pixelized PSF with three peaks
    pixpsf = (np.exp(-0.5 * ((xx-cx1 )**2 + (yy-cy1)**2 + 
                             (xx-cx1)*(yy-cy1)*co)/ 1.**2) +
              np.exp(-0.5 * ((xx-34.5)**2 + (yy-28)**2) / 1.**2) +
              np.exp(-0.5 * ((xx-34  )**2 + (yy-34)**2) / 1.**2))

    plt.clf()
    plt.imshow(pixpsf, interpolation='nearest', origin='lower', cmap='gray')
    plt.title('Pixelized PSF model')
    plt.savefig('demo-0.png')

    re = 16.
    e1 = -0.25
    e2 =  0.5

    cd = np.array([[ 1e-3, 4e-5],
                   [ 5e-5, 1.1e-3]])

    G = galaxy_psf_convolution(re, e1, e2, ExpGalaxy, cd, 0., 0., pixpsf)

    plt.clf()
    plt.imshow(G, interpolation='nearest', origin='lower', cmap='gray')
    plt.title('Exp Galaxy')
    plt.savefig('demo-1.png')

    G = galaxy_psf_convolution(re, e1, e2, ExpGalaxy, cd, 0.5, 0., pixpsf)

    plt.clf()
    plt.imshow(G, interpolation='nearest', origin='lower', cmap='gray')
    plt.title('Exp Galaxy (shifted)')
    plt.savefig('demo-2.png')

    # DeV profile

    G = galaxy_psf_convolution(re, e1, e2, DevGalaxy, cd, 0.5, 0., pixpsf)

    plt.clf()
    plt.imshow(G, interpolation='nearest', origin='lower', cmap='gray')
    plt.title('DeV Galaxy')
    plt.savefig('demo-3.png')
    
    # Tiny re
    re = 0.1
    
    G = galaxy_psf_convolution(re, e1, e2, ExpGalaxy, cd, 0.5, 0., pixpsf)

    plt.clf()
    plt.imshow(G, interpolation='nearest', origin='lower', cmap='gray')
    plt.title('Compact Galaxy')
    plt.savefig('demo-4.png')

    
