# Icon files

Icons are 250x250 greyscale PNG images with black paint and a transparent background, and
used only by `bdedit`. Icons are black "ink" with a transparent background.

Icon names are all lower-case versions of the CamelCase class name, eg. the class `Gain` has the icon file named `gain.png`.

![gain.png](https://github.com/petercorke/bdsim/raw/master/bdsim/blocks/Icons/gain.png)

Icons are drawn to be interpretted with inputs on the left and outputs on the right.  Icons can be flipped so that inputs are on the right, and
if it makes sense for an alternative icon in that situation its name has the `_flipped` suffix.  For the case of the `Gain` block that would be `gain_flipped.png`

![gain_flipped.png](https://github.com/petercorke/bdsim/raw/master/bdsim/blocks/Icons/gain_flipped.png)

The bulk of icons are defined in this folder, but blocks can be imported from folders in other toolboxes.  In that case, the `Icons` folder
in those folders contains the corresponding icon files.

# Creating icons from LaTeX

Icons are created by the script `bdtex2icon` which is run like this from the `Icons` folder

```
bdtex2icon -r 300 -o sum.png -t '\sum'
```

where the `-o` option specifies the name of the output file and the `-t` option is
the LaTeX string. The `-r` option is the resolution or scale of the icon.  If it is too
big or too small it will suggest a better value for resolution.  Choose a value just
under the recommended value, check that that `bdtex2icon` is happy with the value and
inspect the icon file.

Add the line to the file `icons.sh` which is a shell script that builds all icon files.

**Note that you must have a working LaTeX installation that includes `pdflatex`, `pdfcrop`
and `gs`**