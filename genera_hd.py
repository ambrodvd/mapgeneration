import argparse
import contextily as cx
import matplotlib.pyplot as plt

PAPER_SIZES = {"A1": (33.1, 23.4), "A2": (23.4, 16.5)}

parser = argparse.ArgumentParser()
parser.add_argument("--lat_min", type=float, required=True)
parser.add_argument("--lat_max", type=float, required=True)
parser.add_argument("--lon_min", type=float, required=True)
parser.add_argument("--lon_max", type=float, required=True)
parser.add_argument("--size", choices=["A1", "A2"], required=True)
parser.add_argument("--dpi", type=int, required=True)
parser.add_argument("--zoom", default="auto", help="auto o un numero")
args = parser.parse_args()

w_in, h_in = PAPER_SIZES[args.size]

fig, ax = plt.subplots(figsize=(w_in, h_in), dpi=args.dpi)
ax.set_xlim(args.lon_min, args.lon_max)
ax.set_ylim(args.lat_min, args.lat_max)
ax.set_axis_off()

zoom_param = int(args.zoom) if args.zoom != "auto" else "auto"
cx.add_basemap(ax, source=cx.providers.OpenTopoMap, crs="EPSG:3857", zoom=zoom_param, attribution_size=6)
fig.tight_layout(pad=0)

output = f"mappa_{args.size}_{args.dpi}dpi.png"
fig.savefig(output, dpi=args.dpi, bbox_inches="tight", pad_inches=0)
plt.close(fig)
print(f"Salvato: {output}")