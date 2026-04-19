#!/usr/bin/env python3
from __future__ import annotations

import argparse
import tempfile
import os
import sys
import subprocess
import io
from PIL import Image, ImageOps
from pathlib import Path
import numpy as np

latex_template_rvc = """\\documentclass{{article}}
\\thispagestyle{{empty}}
\\usepackage{{graphicx}} % \\scalebox
\\input{{rvc-notation}}
\\begin{{document}}
${tex}$
\\end{{document}}
"""

latex_template_norvc = """\\documentclass{{article}}
\\thispagestyle{{empty}}
\\usepackage{{graphicx}} % \\scalebox
\\begin{{document}}
${tex}$
\\end{{document}}
"""

IMSIZE = 250


def main():
    des = "tex2icon, create bdedit icons from LaTeX source"
    parser = argparse.ArgumentParser(description=des)
    parser.add_argument(
        "-t",
        help="The LaTeX string to convert",
        required=True,
        metavar='"LaTeX string"',
    )
    parser.add_argument(
        "-r", help="resolution (dpi)", type=int, default=100, metavar='"resolution"'
    )
    parser.add_argument(
        "-o", help="The output filename.", default="icon.png", metavar="filename"
    )
    parser.add_argument(
        "-v",
        "--verbose",
        help="be verbose.",
        default=False,
        action="store_const",
        const=True,
        metavar="verbose",
    )
    args = parser.parse_args()

    # look for rvc-notation on LaTeX path, see https://github.com/petercorke/rvc-notation
    try:
        subprocess.run(
            ["kpsewhich", "rvc-notation.tex"], stdout=subprocess.DEVNULL, check=True
        )
        latex_template = latex_template_rvc
        if args.verbose:
            print("RVC macros found")
    except subprocess.CalledProcessError:
        latex_template = latex_template_norvc
        if args.verbose:
            print("RVC macros not found")

    # build the icon
    try:
        # create LaTeX source file in temp file
        source_filename = tempfile.mkstemp(suffix=".tex", text=True)
        os.write(source_filename[0], latex_template.format(tex=args.t).encode("utf8"))
        os.close(source_filename[0])

        # run pdflatex, results go to temp folder
        source_path = Path(source_filename[1])
        if args.verbose:
            print("run pdflatex on ", source_path)
        subprocess.run(
            ["pdflatex", "-output-directory", source_path.parent, source_path.name],
            stdout=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            check=True,
        )

        # run pdfcrop to remove all that white space
        if args.verbose:
            print("run pdfcrop")
        subprocess.run(
            ["pdfcrop", source_path.with_suffix(".pdf")],
            check=True,
            stdout=subprocess.DEVNULL,
        )

        # get path to -crop.pdf file
        cropped_filename = source_path.with_name(
            source_path.stem + "-crop"
        ).with_suffix(".pdf")
        print(cropped_filename)

        # run gs to convert cropped pdf to png file
        # user can control the resolution to scale the icon
        gs_args = [
            "/usr/local/bin/gs",
            "-sDEVICE=pngalpha",
            "-sOutputFile=%stdout",
            "-r" + str(args.r * 5),
            "-dBATCH",
            "-dNOPAUSE",
            "-q",
            "-dGraphicsAlphaBits=4",
            "-dDOINTERPOLATE",
            str(cropped_filename),
        ]
        if args.verbose:
            print("run gs")
        gs = subprocess.Popen(
            gs_args, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
        )

        # read image data from gs into a PIL image
        image = Image.open(gs.stdout)
        gs.stdout.close()

        # display image size
        w, h = image.size
        print(f"icon is {h} x {w} pixels")
        print("suggest change scale factor to ", int(args.r * IMSIZE / max(w, h)))

        # check if it's too big for bdedit
        if max(w, h) >= IMSIZE:
            sys.exit(1)

        # use NumPy to centre the image into a 50x50 background & invert it
        # use the alpha plane as greyscale since it has the antialiasing
        img = np.array(image)[:, :, 3]
        roff = (IMSIZE - h) // 2
        coff = (IMSIZE - w) // 2
        icon = np.full((IMSIZE, IMSIZE), 255, np.uint8)  # white background
        icon[roff : roff + h, coff : coff + w] = 255 - img  # black text

        # now convert to RGBA image
        icon_rgba = np.empty((IMSIZE, IMSIZE, 4), np.uint8)
        for i in range(3):
            icon_rgba[:, :, i] = icon
        icon_rgba[:, :, 3] = np.where(icon == 255, 0, 255)

        # convert back to Image and save it
        Image.fromarray(icon_rgba).save(args.o)
        print("icon saved --> ", args.o)

    except (OSError, ValueError, subprocess.CalledProcessError):
        print("exception during processing pipeline, requires: pdflatex, gs, pdfcrop")

    # cleanup all the temporary files
    for suffix in (".aux", ".log", ".pdf", ".tex"):
        source_path.with_suffix(suffix).unlink(missing_ok=True)

    try:
        cropped_filename.unlink(missing_ok=True)
    except UnboundLocalError:
        pass


if __name__ == "__main__":
    try:
        from ._selftest import run_module_test
    except ImportError:
        from bdsim._selftest import run_module_test

    raise SystemExit(run_module_test(__file__))
