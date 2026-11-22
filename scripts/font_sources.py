"""Load the upstream faces and interpolate Office Code Pro's Retina outlines."""

from contextlib import ExitStack, closing, contextmanager
from pathlib import Path
import subprocess
import tempfile

import fontforge

from font_config import STYLES


def office_font(directory, style):
    path = directory / "Fonts/Office Code Pro/OTF" / ("OfficeCodePro-" + style + ".otf")
    return closing(fontforge.open(str(path)))


@contextmanager
def open_sources(args, style):
    weight = style.removesuffix("Italic")
    italic = style.endswith("Italic")
    with ExitStack() as stack:
        office = stack.enter_context(office_font(args.office_dir, style.replace("Retina", "Regular")))
        medium = None
        if weight == "Retina":
            medium = stack.enter_context(office_font(args.office_dir, style.replace("Retina", "Medium")))
            slant = "Italic" if italic else "Upright"
            variable = args.source_dir / "VF" / ("SourceCodeVF-" + slant + ".otf")
            staging = stack.enter_context(tempfile.TemporaryDirectory())
            donor_path = Path(staging) / "donor.otf"
            # FontForge needs CFF1 outlines to read a static instance of a CFF2 font.
            subprocess.run([args.fonttools, "varLib.instancer", "-q", "--downgrade-cff2",
                            str(variable), "wght=%d" % STYLES[style], "-o", str(donor_path)], check=True)
        else:
            donor_style = "It" if style == "RegularItalic" else style.replace("Italic", "It")
            donor_path = args.source_dir / "OTF" / ("SourceCodePro-" + donor_style + ".otf")
        donor = stack.enter_context(closing(fontforge.open(str(donor_path))))
        if donor.os2_weight != STYLES[style]:
            raise ValueError("Unexpected Source Code Pro weight for " + style)
        fira_path = args.ligaturizer_dir / "fonts/fira/distr/otf" / ("FiraCode-" + weight + ".otf")
        fira = stack.enter_context(closing(fontforge.open(str(fira_path))))
        regular_fira = None
        if weight == "Retina":
            regular_path = fira_path.with_name("FiraCode-Regular.otf")
            regular_fira = stack.enter_context(closing(fontforge.open(str(regular_path))))
            if not regular_fira.os2_weight < STYLES[style] <= fira.os2_weight:
                raise ValueError("Ligature weight outside Fira Code Regular and Retina")
        elif fira.os2_weight != STYLES[style]:
            raise ValueError("Unexpected Fira Code weight for " + style)
        yield office, medium, donor, fira, regular_fira


def compatible_layers(glyph, medium):
    name = glyph.glyphname
    left, right = glyph.foreground, medium[name].foreground
    italic = bool(medium.italicangle)
    if name == "percent":
        # Medium stores the lower counter and the lower slash in reverse order.
        right[4], right[5] = right[5], right[4]
    elif name == "uni1E97":
        # Medium merges one dot into the t. Restore the components at its accent position.
        dots = medium["dieresis"].foreground
        mark, origin = right[1][0], dots[0][0]
        dots.transform((1, 0, 0, 1, mark.x - origin.x, mark.y - origin.y))
        right = dots + medium["t"].foreground
    elif name == "eogonek":
        # A short edge at the ogonek join collapses to one point in Medium.
        contour = right[0]
        join = 30 if italic else 33
        contour.insertPoint(contour[join], join)
        right[0] = contour
    elif italic and name in ("aogonek", "uogonek"):
        contour = right[0]
        contour.makeFirst(6)
        right[0] = contour
        if name == "aogonek":
            # Here the corresponding edge collapses in Regular.
            contour = left[0]
            contour.insertPoint(contour[13], 13)
            left[0] = contour
    return left, right


def on_curve_counts(layer):
    return [sum(point.on_curve for point in contour) for contour in layer]


def interpolate_outline(left, right, fraction, name):
    # FontForge can silently truncate a contour if on-curve point counts differ.
    if on_curve_counts(left) != on_curve_counts(right):
        raise ValueError("Incompatible interpolation outlines: " + name)
    outline = left.interpolateNewLayer(right, fraction)
    outline.round()
    return outline


def fira_layers(regular, retina, name):
    left, right = regular[name].foreground, retina[name].foreground
    if name == "numbersign_underscore_parenleft.liga":
        # Fira's Retina starts the inner contour one corner later than Regular.
        counter = right[1]
        counter.makeFirst(3)
        right[1] = counter
    return left, right


def interpolate_ligatures(regular, retina, weight, specs):
    fraction = (weight - regular.os2_weight) / (retina.os2_weight - regular.os2_weight)
    for name in sorted({spec["firacode_ligature_name"] for spec in specs.values()}):
        if name not in retina:
            continue
        glyph = retina[name]
        left, right = fira_layers(regular, retina, name)
        glyph.foreground = interpolate_outline(left, right, fraction, name)
        glyph.autoHint()


def interpolate_retina(regular, medium, bold, weight):
    fraction = (weight - regular.os2_weight) / (medium.os2_weight - regular.os2_weight)
    stem = regular.private["StdVW"][0]
    bold_fraction = fraction * (medium.private["StdVW"][0] - stem) / (bold.private["StdVW"][0] - stem)
    for key in ("BlueValues", "StdHW", "StdVW", "StemSnapH", "StemSnapV"):
        regular.private[key] = tuple(round(a + fraction * (b - a))
                                     for a, b in zip(regular.private[key], medium.private[key]))
    shift = regular.private["BlueShift"]
    regular.private["BlueShift"] = round(shift + fraction * (medium.private["BlueShift"] - shift))

    for glyph in regular.glyphs():
        name = glyph.glyphname
        if name in ("ellipsis", "second"):
            # Medium fuses repeated dots/primes. Bold has the distinct contours.
            left, right = glyph.foreground, bold[name].foreground
            outline = interpolate_outline(left, right, bold_fraction, name)
        else:
            left, right = compatible_layers(glyph, medium)
            outline = interpolate_outline(left, right, fraction, name)
        if name == "uni1E97" and outline.selfIntersects():
            outline.removeOverlap()
            outline.round()
        glyph.foreground = outline
        glyph.autoHint()
