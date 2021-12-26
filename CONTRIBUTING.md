# Contributing

This is a small-scale private project with a team size of about 0.01. I'd be delighted if you'd like to use and apply the tool, or even to contribute.

## Communicating
GitHub Issues is a convenient means to discuss bugs or possible contributions.

## Bug notifications
If you're using bdsim and encounter errors with the latest version from GitHub then please report it through GitHib Issues.  Be sure to include:

* a description of what the issue is, and the stack trace you get
* the version of Python and numpy that you are using
* a runnable code example that demonstrates the issue

## Specific contributions needed

* The numerical integrator from SciPy has some limitations.  It cannot handle:
  *  hybrid continuous-discrete systems, 
  *  events associated with strong non-linearities or discontinuous inputs,
  *  allow the state vector to be updated (ie. as would be required to renormalize a unit-quaternion state).
* Extend to support bond graphs, or a hybrid of bond graphs and block diagrams.
* There are many more blocks that could be created but of immediate interest are:
  * real-time blocks that interface to ADCs, DACs and PWM channels for use on a RaspberryPi
  * vision blocks that interface to cameras, displays and OpenCV operators

## Other contributions

These are welcome but it'd be great to discuss through GitHub Issues before you start.  You will be acknowledged as the author, but by contributing you are agreeing to your work being shared under the MIT Licence.  Contributions should have unit tests and good quality documentation.

## Feature requests
These are unlikely to be implemented by me, it's a time thing...

## Any contributions you make will be under the MIT Software License
In short, when you submit code changes, your submissions are understood to be under the same [MIT License](http://choosealicense.com/licenses/mit/) that covers the project. 

## Code of conduct

So far there isn't one, but if there were it would embed principles from the [Contributor Covenant Code Of Conduct](https://www.contributor-covenant.org/version/1/4/code-of-conduct).

