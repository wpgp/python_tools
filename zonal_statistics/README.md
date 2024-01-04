# Python command line tools

This folder contains several command line tools for performing zonal statistics around points. Most of the tools are built upon the following packages such that installing them are necessary:
- [numpy](https://numpy.org)
- [pandas](https://pandas.pydata.org)
- [geopandas](https://geopandas.org)
- [rasterio](https://rasterio.readthedocs.io)
- [rasterstats](https://pythonhosted.org/rasterstats/)
- [scipy](https://scipy.org)
- [shapely](https://shapely.readthedocs.io/en/stable/manual.html)

To install the required package, open the command prompt or [Anaconda](https://www.anaconda.com) and use `pip install [package name]`. Alternatively, `conda install [package name]` can also be used in the Anaconda.

### Preparing Buffers
`get_buffer.py` is a script to create buffers surrounding points of interest. This can be supplied with CSV containing geocoordinates (lat,lon) or vector file with valid geometries. Type `python get_buffer.py --help` to know how to use this script.

Example:
```
# Create buffer from points listed in sample/Aden.csv
python get_buffer.py --input sample/Aden.csv --rad 5 --clip --output sample/Aden

# Create buffer from points listed in sample/Aden_1.gpkg
python get_buffer.py --input sample/Aden_1.gpkg --rad 10 --clip --output sample/Aden

# Update sample/Aden.gpkg by adding extra buffers from 
# sample/Aden2.gpkg
python get_buffer.py --input sample/Aden_10km_clipped.gpkg --add sample/Aden_2.gpkg --clip --output sample/Aden
```
### Performing Zonal Statistics
`zonal_statistics.py` is a script to extract zonal statistics from raster input based on the list of features provided. Copy the script to the working directory to use it. Type `python zonal_statistics.py --help` to know how to use this script.

### Extracting Population Count from WorldPop Dataset
