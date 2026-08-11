import gdstk
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from matplotlib.collections import PatchCollection
import itertools
from collections import defaultdict

lib = gdstk.read_gds("runs/RUN_2026-08-11_18-46-58/final/gds/tt_um_rtfce.gds")
top = lib.top_level()[0]

all_polys = top.get_polygons()
by_layer = defaultdict(list)
for p in all_polys:
    by_layer[(p.layer, p.datatype)].append(p)

print(f"Number of distinct layers: {len(by_layer)}")

fig, ax = plt.subplots(figsize=(14, 10))

color_cycle = itertools.cycle([
    "#8B0000", "#FF8C00", "#DAA520", "#228B22", "#00CED1",
    "#1E90FF", "#4B0082", "#C71585", "#708090", "#2F4F4F",
    "#B22222", "#FF69B4", "#32CD32", "#4682B4", "#9370DB",
])

for (layer, datatype), polys in by_layer.items():
    color = next(color_cycle)
    patches = [Polygon(p.points, closed=True) for p in polys]
    pc = PatchCollection(patches, facecolor=color, edgecolor="none", alpha=0.9)
    ax.add_collection(pc)

ax.autoscale()
ax.set_aspect('equal')
ax.set_title("tt_um_rtfce - Baseline RTFCE Physical Layout (SkyWater 130nm)\nColor = GDS layer/datatype")
ax.set_xlabel("X (microns)")
ax.set_ylabel("Y (microns)")
ax.set_facecolor("black")
plt.tight_layout()
plt.savefig("rtfce_layout_colored.png", dpi=200, facecolor="black")
print("Saved rtfce_layout_colored.png")
