from setuptools import setup, find_packages
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

# Get the release/version string
with open(path.join(here, 'RELEASE'), encoding='utf-8') as f:
    release = f.read()


setup(
    name='bdsim', 

    version=release,

    # This is a one-line description or tagline of what your project does. This
    # corresponds to the "Summary" metadata field:
    description='Simulate dynamic systems expressed in block diagram form using Python.', #TODO
    
    long_description=long_description,
    long_description_content_type='text/markdown',

    classifiers=[
    #   3 - Alpha
    #   4 - Beta
    #   5 - Production/Stable
    'Development Status :: 4 - Beta',

    # Indicate who your project is intended for
    'Intended Audience :: Developers',
    # Pick your license as you wish (should match "license" above)
     'License :: OSI Approved :: MIT License',

    # Specify the Python versions you support here. In particular, ensure
    # that you indicate whether you support Python 2, Python 3 or both.
    'Programming Language :: Python :: 3 :: Only'],

    project_urls={
        #'Documentation': 'https://petercorke.github.io/bdsim',
        'Source': 'https://github.com/petercorke/bdsim',
        'Tracker': 'https://github.com/petercorke/bdsim/issues',
        #'Coverage': 'https://codecov.io/gh/petercorke/spatialmath-python',
    },

    url='https://github.com/petercorke/bdsim',

    author='Peter Corke',

    author_email='rvc@petercorke.com', #TODO

    keywords='python block-diagram dynamic simulation',

    license='MIT', #TODO

    python_requires='>=3.6',

    packages=find_packages(exclude=["test_*", "TODO*"]),

    install_requires=['numpy', 'scipy', 'matplotlib', 'ansitable', 'colored', 'spatialmath-python']
    
)
