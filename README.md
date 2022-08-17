# Python command line tools

This module contains several command line tools that might be useful for spatial data analysis and modelling. The development of these tools aims for the ease of use. Most of the tools are built upon the following packages such that installing them are necessary:
- [numpy](https://numpy.org)
- [pandas](https://pandas.pydata.org)
- [geopandas](https://geopandas.org)
- [rasterio](https://rasterio.readthedocs.io)
- [rasterstats](https://pythonhosted.org/rasterstats/)

To install the required package, open the command prompt or [Anaconda](https://www.anaconda.com) and use `pip install [package name]`. Alternatively, `conda install [package name]` can also be used in the Anaconda.

### Zonal Statistics
`zonal_statistics.py` is a script to extract zonal statistics from raster input based on the list of features provided. Copy the script to the working directory to use it. Type `python zonal_statistics.py --help` to know how to use this script.

### Dynamic World Wrapper
`dworld_wrapper.py` can be used to acquire [Dynamic World](https://dynamicworld.app) land use/land cover (LULC) class for a specific area. Tiles of annually aggregated Dynamic World data (from 2016-2021) are available at the WorldPop drive. The `dworld_wrapper.py` script helps to merge and clip the tiles.

Usage: `python dworld_wrapper.py -y year -b band -c boundary -o output.tif`
- Available years: 2016, 2017, 2018, 2019, 2020, 2021
- Available bands: water, trees, grass, flooded_vegetation, crops, shrub_and_scrub, built, bare, snow_and_ice
- Clipping boundary: can either be a shapefile or coordinate boundary (xmin, xmax, ymin, ymax)
