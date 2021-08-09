#!/usr/bin/env python3

import argparse
import tempfile
import os
import sys
import subprocess
import io
from PIL import Image, ImageOps
from pathlib import Path
import numpy as np

latex_template = """\\documentclass{{article}}
\\thispagestyle{{empty}}
\\usepackage{{graphicx}} % \\scalebox
\\input{{rvc-notation}}
\\begin{{document}}
${tex}$
\\end{{document}}"""

IMSIZE = 250

def main():
    des = 'tex2icon, create bdedit icons from LaTeX source'
    parser = argparse.ArgumentParser(description=des)
    parser.add_argument('-t', help='The LaTeX string to convert',
                        required=True, metavar='"LaTeX string"')
    parser.add_argument('-r', help='resolution (dpi)', type=int, default=100,
                        metavar='"resolution"')
    parser.add_argument('-o', help='The output filename.', default='icon.png', metavar='filename')
    args = parser.parse_args()

    try:
        # create LaTeX source file in temp file
        source_filename = tempfile.mkstemp(suffix='.tex', text=True)
        os.write(source_filename[0], latex_template.format(tex=args.t).encode('utf8'))
        os.close(source_filename[0])

        # run pdflatex, results go to temp folder
        source_path = Path(source_filename[1])
        subprocess.run(["pdflatex", "-output-directory", source_path.parent, source_path.name], 
            stdout=subprocess.DEVNULL)
        # print(source_filename[1])

        # run pdfcrop to remove all that white space
        subprocess.run(["pdfcrop", source_path.with_suffix('.pdf')], stdout=subprocess.DEVNULL)

        # get path to -crop.pdf file
        cropped_filename = source_path.with_name(source_path.stem + '-crop').with_suffix('.pdf')
        # print(cropped_filename)

        # run gs to convert cropped pdf to png file
        # user can control the resolution to scale the icon
        gs_args = [
                '/usr/local/bin/gs',
                '-sDEVICE=pngalpha',
                '-sOutputFile=%stdout',
                '-r' + str(args.r * 5),
                '-dBATCH',
                '-dNOPAUSE',
                '-q',
                '-dGraphicsAlphaBits=4',
                '-dDOINTERPOLATE',
                str(cropped_filename)
            ]
        gs = subprocess.Popen(gs_args, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

        # read image data from gs into a PIL image
        image = Image.open(gs.stdout) 
        gs.stdout.close()

        # display image size
        w, h = image.size
        print(f'icon is {h} x {w} pixels')

        # check if it's too big for bdedit
        if max(w, h) >= IMSIZE:
            sys.exit(1)
        print('suggest change scale factor to ', int(args.r * IMSIZE / max(w, h)))

        # A plane is 0 for backgroud, 255 for foreground, and antialias values
        # in between
        A = np.array(image)[:,:,3]

        # use NumPy to centre the alpha plane into fixed size background & invert
        roff = (IMSIZE - h) // 2
        coff = (IMSIZE - w) // 2
        icon = np.full((IMSIZE, IMSIZE), 255, np.uint8)
        icon[roff:roff+h, coff:coff+w] = 255 - A

        # grey scale image now centred in icon
        # 255 for background, 0 for foreground

        # make background transparent
        out = []
        for pixel in icon.ravel():  # iterate over the A plane
            if pixel == 255:
                # make background transparent
                out.append((255, 255, 255, 0))
            else:
                # foreground incl. antialiased values
                out.append((pixel, pixel, pixel, 255))

        # create new RGBA image
        iconimage = Image.new('RGBA', size=(IMSIZE, IMSIZE))
        iconimage.putdata(out)

        # save it
        iconimage.save(args.o)
        print('icon saved --> ', args.o)

    except (OSError, ValueError):
        print('exception during processing pipeline')

    # cleanup all the temporary files
    for suffix in ('.aux', '.log', '.pdf', '.tex'):
        source_path.with_suffix(suffix).unlink(missing_ok=True)
    cropped_filename.unlink(missing_ok=True)

if __name__ == '__main__':
    main()