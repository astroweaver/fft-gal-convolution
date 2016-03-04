import matplotlib
matplotlib.use('Agg')
import pylab as plt
from astrometry.util.plotutils import *
from astrometry.util.util import Tan

import tractor
from tractor import *
from tractor.galaxy import *


egal = EllipseE.fromRAbPhi(16., 0.3, 120.)
print 'egal', egal
cx,cy = 0,0
H,W = 100,100
data=np.zeros((H,W), np.float32)
tinypsf = NCircularGaussianPSF([0.01], [1.])
#wcs = None
cd11 = 1.e-3
cd22 = 1.1e-3
cd12 = 4.e-5
cd21 = 5e-5
wcs = ConstantFitsWcs(Tan(0., 0., 0., 0., cd11, cd12, cd21, cd22, 0., 0.))

img = Image(data=data, invvar=np.ones_like(data), psf=tinypsf, wcs=wcs)
gal = ExpGalaxy(PixPos(cx,cy), Flux(100.), egal)
amix = gal._getAffineProfile(img, cx, cy)

#print 'amix', amix

Vnew = amix.var[0,:,:]
print 'Vnew', Vnew

# expgalaxy mixture variance 0
v0 = 1.20078965e-03

cd = img.getWcs().cdAtPixel(cx,cy)
print 'cd', cd
theta = egal.theta
print 'theta', theta
c = np.cos(theta)
s = np.sin(theta)
e = egal.e
#a = (1 - e) / (1 + e)
a = (1 + e) / (1 - e)
print 'a', a
r = egal.re
print 'r', r

# G = egal.getRaDecBasis()
# print 'G', G
# print 'g11', r/3600. * c/a
# print 'g12', r/3600. * s

t = cd[0,0]
u = cd[0,1]
v = cd[1,0]
w = cd[1,1]
Vfactor = (r / 3600. / (t*w-u*v))**2
print 'Vfactor', Vfactor
v11 = Vfactor * (1/a**2 * (w**2*c**2 + 2*u*w*c*s + u**2*s**2)
                 + w**2*s**2 - 2*u*w*c*s + u**2*c**2)
print 'v11', v11

v22 = Vfactor * (1/a**2 * (v**2*c**2 + 2*t*v*c*s + t**2*s**2)
                 + t**2*c**2 - 2*t*v*c*s + v**2*s**2)
print 'v22', v22

v12 = Vfactor * (-1/a**2 * (v*w*c**2 + u*v*c*s + t*w*c*s + t*u*s**2)
                 - v*w*s**2 + u*v*c*s + t*w*c*s - t*u*c**2)
print 'v12', v12

# No need to compute sin/cos!
e = egal.e
e1 = egal.e1
e2 = egal.e2
c2 = 0.5 * (1 + e1/e)
s2 = 0.5 * (1 - e1/e)
cs = 0.5 * e2/e

v11e = Vfactor * (1/a**2 * (w**2*c2 + 2*u*w*cs + u**2*s2)
                 + w**2*s2 - 2*u*w*cs + u**2*c2)
print 'v11e', v11e

v22e = Vfactor * (1/a**2 * (v**2*c2 + 2*t*v*cs + t**2*s2)
                 + t**2*c2 - 2*t*v*cs + v**2*s2)
print 'v22e', v22e

v12e = Vfactor * (-1/a**2 * (v*w*c2 + u*v*cs + t*w*cs + t*u*s2)
                 - v*w*s2 + u*v*cs + t*w*cs - t*u*c2)
print 'v12e', v12e


ph,pw = 64,64
xx,yy = np.meshgrid(np.arange(pw), np.arange(ph))
cx1,cy1 = 28,28
co = 0.7
pixpsf = (np.exp(-0.5 * ((xx-cx1 )**2 + (yy-cy1)**2 + (xx-cx1)*(yy-cy1)*co)/ 1.**2) +
          np.exp(-0.5 * ((xx-34.5)**2 + (yy-28)**2) / 1.**2) +
          np.exp(-0.5 * ((xx-34  )**2 + (yy-34)**2) / 1.**2))

plt.clf()
plt.imshow(pixpsf, interpolation='nearest', origin='lower', cmap='gray')
plt.savefig('demo-0.png')

P = np.fft.rfft2(pixpsf)
pH,pW = pixpsf.shape
v = np.fft.rfftfreq(pW)
w = np.fft.fftfreq(pH)

# magic arrays, generated by running optimize_mixture_profiles.py:
# (note optimize_mixture_profiles.py now lives in Hogg's TheTractor github repo)
exp_amp = np.array([  2.34853813e-03,   3.07995260e-02,   2.23364214e-01,
              1.17949102e+00,   4.33873750e+00,   5.99820770e+00])
exp_var = np.array([  1.20078965e-03,   8.84526493e-03,   3.91463084e-02,
              1.39976817e-01,   4.60962500e-01,   1.50159566e+00])
exp_amp /= np.sum(exp_amp)

#Vt = np.array([[v11e, v12e],[v12e,v22e]])

print('v:', len(v))
print('w:', len(w))

Fsum = np.zeros((len(w), len(v)), np.complex128)
for amp,var in zip(exp_amp, exp_var):
    #Vnew = v0 * Vt
    a = var * v11e
    b = var * v12e
    d = var * v22e
    F = (np.exp(-2. * np.pi**2 *
                (a * v[np.newaxis,:]**2 +
                 d * w[:,np.newaxis]**2 +
                 2*b*v[np.newaxis,:]*w[:,np.newaxis])))
    Fsum += amp * F

# Factor out inner exp() evaluation
Fsum = np.zeros((len(w), len(v)), np.complex128)

F1 = np.exp(-2. * np.pi**2 *
            (  v11 * v[np.newaxis,:]**2 +
               v22 * w[:,np.newaxis]**2 +
             2*v12 * v[np.newaxis,:]*w[:,np.newaxis]))
for amp,var in zip(exp_amp, exp_var):
    Fsum += amp * F1**var

# Factor out inner arg of exp
Fsum = np.zeros((len(w), len(v)), np.complex128)
ee = (-2. * np.pi**2 *
      (  v11 * v[np.newaxis,:]**2 +
         v22 * w[:,np.newaxis]**2 +
       2*v12 * v[np.newaxis,:]*w[:,np.newaxis]))
for amp,var in zip(exp_amp, exp_var):
    Fsum += amp * np.exp(ee * var)
    
mu = [0,0]
Fsum *= np.exp(-2.*np.pi* 1j *(mu[0]*v[np.newaxis,:] +
                               mu[1]*w[:,np.newaxis]))
    


G = np.fft.irfft2(Fsum * P, s=(pH,pW))

plt.clf()
plt.imshow(G, interpolation='nearest', origin='lower', cmap='gray')
plt.savefig('demo-1.png')