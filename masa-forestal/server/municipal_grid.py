"""Rejillas de consulta municipales; núcleos disjuntos y alineados a 20 m."""
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.tools/geospatial'))
from pyproj import Transformer
from shapely.geometry import shape, box, mapping
from shapely.ops import transform

GRID_VERSION = 'municipal-utm14-20m-v1'


def municipal_blocks(geometry, resolution=20, side=800):
    """Devuelve solo intersecciones con área; ningún bloque pierde islas o huecos."""
    if resolution != 20 or not isinstance(side, int) or not 1 <= side <= 1000:
        raise ValueError('Parámetros de bloque fuera del método verificado.')
    polygon = shape(geometry)
    if polygon.is_empty or not polygon.is_valid or polygon.geom_type not in ('Polygon', 'MultiPolygon'):
        raise ValueError('Geometría municipal inválida.')
    projected = transform(Transformer.from_crs(4326, 32614, always_xy=True).transform, polygon)
    left, bottom, right, top = projected.bounds
    left, bottom = math.floor(left / resolution) * resolution, math.floor(bottom / resolution) * resolution
    right, top = math.ceil(right / resolution) * resolution, math.ceil(top / resolution) * resolution
    step = side * resolution
    blocks = []
    for y in range(bottom, top, step):
        for x in range(left, right, step):
            bounds = [x, y, min(x + step, right), min(y + step, top)]
            clipped = projected.intersection(box(*bounds))
            if clipped.is_empty or clipped.area <= 0:
                continue
            if clipped.geom_type == 'GeometryCollection':
                from shapely.ops import unary_union
                clipped = unary_union([g for g in clipped.geoms if g.geom_type in ('Polygon', 'MultiPolygon')])
            blocks.append((f'{x}-{y}', bounds, mapping(clipped)))
    if not blocks:
        raise ValueError('El municipio no produce bloques de consulta.')
    return blocks
