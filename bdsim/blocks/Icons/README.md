Icons are 250x250 greyscale PNG images with black paint and a transparent background.

Icon names are all lower-case versions of the CamelCase class name, eg. the class `Gain` has the icon file named `gain.png`.

![gain.png](https://github.com/petercorke/bdsim/blob/master/bdsim/blocks/Icons/gain.png)

Icons are drawn to be interpretted with inputs on the left and outputs on the right.  Icons can be flipped so that inputs are on the right, and
if it makes sense for an alternative icon in that situation it's name has the `_flipped` suffix.  For the case of the `Gain` block that would be
`gain_flipped.png`

![gain_flipped.png](https://github.com/petercorke/bdsim/blob/master/bdsim/blocks/Icons/gain_flipped.png)

The bulk of icons are defined in this folder, but blocks can be imported from folders in other toolboxes.  In that case, the `Icons` folder
in those folders contains the corresponding icon files.
