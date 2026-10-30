"""Shared chart look: light and dark themes, thin marks, hairline grid, rounded bar ends.

Sizes are written in CSS pixels (a figure is designed at 800 px wide) and saved at 2x.
Colors: categorical slots 1-3 and the blue/red diverging pair of a palette that was checked
for color-vision deficiency in both themes (worst adjacent CVD delta E 9.2 light / 9.4 dark).
"""
import logging
import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.patches import PathPatch  # noqa: E402
from matplotlib.path import Path  # noqa: E402

# Use Segoe UI (regular + semibold) when the machine has it; otherwise matplotlib falls back to DejaVu Sans.
logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
for _name in ("segoeui.ttf", "seguisb.ttf"):
    _path = pathlib.Path("C:/Windows/Fonts") / _name
    if _path.exists():
        font_manager.fontManager.addfont(str(_path))

PX = 72 / 100  # points per CSS pixel when 1 inch = 100 CSS px
SCALE = 2      # export density

THEMES = {
    "light": {
        "surface": "#fcfcfb", "ink": "#0b0b0b", "ink2": "#52514e", "muted": "#898781",
        "grid": "#e1e0d9", "axis": "#c3c2b7",
        "series": ["#2a78d6", "#eb6834", "#1baf7a"],
        "up": "#2a78d6", "down": "#e34948", "total": "#52514e",
    },
    "dark": {
        "surface": "#1a1a19", "ink": "#f0efec", "ink2": "#c3c2b7", "muted": "#898781",
        "grid": "#2c2c2a", "axis": "#383835",
        "series": ["#3987e5", "#d95926", "#199e70"],
        "up": "#3987e5", "down": "#e66767", "total": "#c3c2b7",
    },
}


def figure(theme, width_px=800, height_px=420, left=70, right=24, top=64, bottom=48):
    """A figure with one axes and fixed margins (in CSS px), so pixel sizes are known."""
    t = THEMES[theme]
    plt.rcParams.update({
        "font.family": ["Segoe UI", "DejaVu Sans", "Arial", "sans-serif"],
        "font.size": 9.5,
        "axes.edgecolor": t["axis"],
        "axes.labelcolor": t["ink2"],
        "xtick.color": t["muted"],
        "ytick.color": t["muted"],
        "xtick.labelcolor": t["ink2"],
        "ytick.labelcolor": t["ink2"],
    })
    fig = plt.figure(figsize=(width_px / 100, height_px / 100), dpi=100 * SCALE, facecolor=t["surface"])
    ax = fig.add_axes([left / width_px, bottom / height_px,
                       1 - (left + right) / width_px, 1 - (top + bottom) / height_px])
    ax.set_facecolor(t["surface"])
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_linewidth(1 * PX)
    ax.tick_params(length=0, pad=6)
    ax.grid(axis="y", color=t["grid"], linewidth=1 * PX, linestyle="-")
    ax.set_axisbelow(True)
    return fig, ax, t


def titles(fig, t, title, subtitle):
    fig.text(0.012 + 0.02, 1 - 18 / (fig.get_figheight() * 100), title, color=t["ink"],
             fontsize=12.5, fontweight="semibold", va="top")
    fig.text(0.012 + 0.02, 1 - 40 / (fig.get_figheight() * 100), subtitle, color=t["ink2"],
             fontsize=9.5, va="top")


def px_to_data(ax, px_x, px_y):
    """Convert CSS px to data units on each axis (limits must already be set)."""
    fig = ax.figure
    w_px = ax.get_position().width * fig.get_figwidth() * 100
    h_px = ax.get_position().height * fig.get_figheight() * 100
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    return px_x * (x1 - x0) / w_px, px_y * (y1 - y0) / h_px


def rounded_bar(ax, x, width, y_base, y_end, color, radius_px=4):
    """A bar from y_base to y_end with 4 px rounded corners at the data end, square at the base."""
    if y_end == y_base:
        return
    rx, ry = px_to_data(ax, radius_px, radius_px)
    rx = min(rx, width / 2)
    ry = min(ry, abs(y_end - y_base))
    left, right = x - width / 2, x + width / 2
    s = 1 if y_end > y_base else -1
    verts = [(left, y_base), (left, y_end - s * ry), (left, y_end), (left + rx, y_end),
             (right - rx, y_end), (right, y_end), (right, y_end - s * ry), (right, y_base), (left, y_base)]
    codes = [Path.MOVETO, Path.LINETO, Path.CURVE3, Path.CURVE3, Path.LINETO,
             Path.CURVE3, Path.CURVE3, Path.LINETO, Path.CLOSEPOLY]
    ax.add_patch(PathPatch(Path(verts, codes), facecolor=color, edgecolor="none"))


MINUS = "−"


def month_label(ym, first=False):
    """'2011-01' -> "Jan '11" for January (or the first tick), else 'Mar'."""
    names = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
    y, m = ym.split("-")
    name = names[int(m) - 1]
    return f"{name} '{y[2:]}" if first or m in ("01", "12") else name


def pct(v, decimals=1):
    return f"{'+' if v > 0 else MINUS if v < 0 else ''}{abs(v):.{decimals}f}%"


def rounded_hbar(ax, y, height, x_base, x_end, color, radius_px=4):
    """A horizontal bar from x_base to x_end, rounded at the data end (right), square at the base."""
    if x_end == x_base:
        return
    rx, ry = px_to_data(ax, radius_px, radius_px)
    ry = min(ry, height / 2)
    rx = min(rx, abs(x_end - x_base))
    bottom, top = y - height / 2, y + height / 2
    s = 1 if x_end > x_base else -1
    verts = [(x_base, bottom), (x_end - s * rx, bottom), (x_end, bottom), (x_end, bottom + ry),
             (x_end, top - ry), (x_end, top), (x_end - s * rx, top), (x_base, top), (x_base, bottom)]
    codes = [Path.MOVETO, Path.LINETO, Path.CURVE3, Path.CURVE3, Path.LINETO,
             Path.CURVE3, Path.CURVE3, Path.LINETO, Path.CLOSEPOLY]
    ax.add_patch(PathPatch(Path(verts, codes), facecolor=color, edgecolor="none"))


def money(v, decimals=0):
    """USD in compact form: 12.9K, 1.4M (typographic minus)."""
    sign = MINUS if v < 0 else ""
    v = abs(v)
    if v >= 1e6:
        return f"{sign}${v / 1e6:.{max(decimals, 1)}f}M"
    if v >= 1e3:
        return f"{sign}${v / 1e3:.{decimals}f}K"
    return f"{sign}${v:.0f}"


def save(fig, path):
    fig.savefig(path, facecolor=fig.get_facecolor())
    plt.close(fig)
