#PyJ2D - Copyright (C) 2011 James Garnon <https://gatc.ca/>
#Released under the MIT License <https://opensource.org/licenses/MIT>

"""
**Transform module**

The module provides surface transformation functionality.
"""

from math import pi as _pi, fabs as _fabs, sin as _sin, cos as _cos, ceil as _ceil
from java.awt.image import BufferedImage, AffineTransformOp
from java.awt import RenderingHints
from java.awt.geom import AffineTransform
from pyj2d.surface import Surface


_deg_rad = _pi/180.0


def rotate(surface, angle):
    """
    Return Surface rotated by the given angle.
    """
    if not angle:
        return surface.copy()
    theta = angle * _deg_rad
    width_i = surface.getWidth()
    height_i = surface.getHeight()
    cos_theta = _fabs( _cos(theta) )
    sin_theta = _fabs( _sin(theta) )
    width_f = int( (width_i * cos_theta) + (height_i * sin_theta) )
    height_f = int( (width_i * sin_theta) + (height_i * cos_theta) )
    surf = Surface((width_f, height_f), BufferedImage.TYPE_INT_ARGB)
    at = AffineTransform()
    at.translate(width_f/2.0, height_f/2.0)
    at.rotate(-theta)
    g2d = surf.createGraphics()
    ot = g2d.getTransform()
    g2d.setTransform(at)
    g2d.setRenderingHint(RenderingHints.KEY_INTERPOLATION,
                         RenderingHints.VALUE_INTERPOLATION_BILINEAR)
    g2d.drawImage(surface, -width_i//2, -height_i//2, None)
    g2d.setTransform(ot)
    g2d.dispose()
    surf._colorkey = surface._colorkey
    surf._alpha = surface._alpha
    return surf


def rotozoom(surface, angle, size):
    """
    Return Surface rotated and resized by the given angle and size.
    """
    if not angle:
        width = int(surface.getWidth() * size)
        height = int(surface.getHeight() * size)
        return scale(surface, (width, height))
    theta = angle * _deg_rad
    width_i = int(surface.getWidth() * size)
    height_i = int(surface.getHeight() * size)
    cos_theta = _fabs( _cos(theta) )
    sin_theta = _fabs( _sin(theta) )
    width_f = int( _ceil((width_i * cos_theta) + (height_i * sin_theta)) )
    if width_f % 2:
        width_f += 1
    height_f = int( _ceil((width_i * sin_theta) + (height_i * cos_theta)) )
    if height_f % 2:
        height_f += 1
    surf = Surface((width_f, height_f), BufferedImage.TYPE_INT_ARGB)
    at = AffineTransform()
    at.translate(width_f/2.0, height_f/2.0)
    at.rotate(-theta)
    g2d = surf.createGraphics()
    ot = g2d.getTransform()
    g2d.setTransform(at)
    g2d.setRenderingHint(RenderingHints.KEY_INTERPOLATION,
                         RenderingHints.VALUE_INTERPOLATION_BILINEAR)
    g2d.drawImage(surface, -width_i//2, -height_i//2, width_i, height_i, None)
    g2d.setTransform(ot)
    g2d.dispose()
    surf._colorkey = surface._colorkey
    surf._alpha = surface._alpha
    return surf


def scale(surface, size, dest=None):
    """
    Return Surface resized by the given size.

    An optional destination surface can be provided.
    """
    if not dest:
        surf = Surface(size, BufferedImage.TYPE_INT_ARGB)
    else:
        surf = dest
    g2d = surf.createGraphics()
    g2d.setRenderingHint(RenderingHints.KEY_INTERPOLATION,
                         RenderingHints.VALUE_INTERPOLATION_BILINEAR)
    g2d.drawImage(surface, 0, 0, size[0], size[1], None)
    g2d.dispose()
    surf._colorkey = surface._colorkey
    surf._alpha = surface._alpha
    return surf


def smoothscale(surface, size, dest=None):
    """
    Return Surface resized by the given size.

    An optional destination surface can be provided.
    Calls scale().
    """
    return scale(surface, size, dest)


def scale2x(surface, dest=None):
    """
    Return Surface resized to twice its size.

    An optional destination surface can be provided.
    """
    return scale(surface,
                 (surface.getWidth()*2, surface.getHeight()*2), dest)


def flip(surface, xbool=True, ybool=False):
    """
    Return Surface that is flipped horizontally, vertically, or both.
    """
    if xbool and ybool:
        at = AffineTransform.getScaleInstance(-1, -1)
        at.translate(-surface.getHeight(), -surface.getHeight())
    elif xbool:
        at = AffineTransform.getScaleInstance(-1, 1)
        at.translate(-surface.getWidth(), 0)
    elif ybool:
        at = AffineTransform.getScaleInstance(1, -1)
        at.translate(0, -surface.getHeight())
    else:
        return surface
    op = AffineTransformOp(at, AffineTransformOp.TYPE_BILINEAR)
    bimage = op.filter(surface, None)
    surf = Surface(bimage)
    surf._colorkey = surface._colorkey
    surf._alpha = surface._alpha
    return surf

