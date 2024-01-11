## Zonal Statistics

This folder contains several scripts for performing zonal statistics around points, especially for extracting population count from the gridded population data. Most of the tools are built upon the following packages such that installing them are necessary:
- [numpy](https://numpy.org)
- [pandas](https://pandas.pydata.org)
- [geopandas](https://geopandas.org)
- [rasterio](https://rasterio.readthedocs.io)
- [rasterstats](https://pythonhosted.org/rasterstats/)
- [scipy](https://scipy.org)
- [shapely](https://shapely.readthedocs.io/en/stable/manual.html)

To install the required package, open the command prompt or [Anaconda](https://www.anaconda.com) and use `pip install [package name]`. Alternatively, `conda install [package name]` can also be used in the Anaconda.

### Preparing Buffers
`get_buffer.py` is a script to create circular buffers surrounding points of interest. This can be supplied with CSV containing geocoordinates (lat,lon) or vector file with valid geometries. Type `python get_buffer.py --help` to know how to use this script.

If non-overlapping buffers are intended, clipping process is performed by pruning the original circular buffers with Voronoi cells generated from the points of interest.

![clipped_buffer](fig/clipped.png)

Example:
```
# Create buffer from points listed in CSV file
python get_buffer.py --input sample/points_1.csv --rad 5 --clip --output sample/points

# Create buffer from points listed in geopackage file
python get_buffer.py --input sample/points_1.gpkg --rad 10 --clip --output sample/points

# Update create file (points_10km_clipped.gpkg) by adding 
# extra buffers from a new geopackage file (points_2.gpkg)
python get_buffer.py --input sample/points_10km_clipped.gpkg --add sample/points_2.gpkg --clip --output sample/points
```

### Extracting Population Count from WorldPop Dataset
WorldPop produces global population count at 100-m and 1-km resolutions. Extended description about the data can be found in [the WorldPop page](https://hub.worldpop.org/project/categories?id=3) and the associated publications mentioned in that page.

Provided this gridded/raster data and the vector data containing the regions of interest (or buffers), the total population at each region can be extracted using `get_population.py`. This script comes together with `config.py` which defines several parameters required for the process. There are:
- `year_start` and `year_end` [integer] : WorldPop provides global gridded population dataset from 2015 to 2023. User can define the dataset epoch from which the extraction is performed, from `year_start` to `year_end`.
- `radii` [list of integer] : radii of circular buffers in kilometer.
- `location` [path-like] : path to file containing the locations of interest or the buffers around the locations. The accepted file should be CSV, XLS, SHP, GPKG, or GEOJSON. The file should contains either `geometry` or `lat-lon` column.
- `location_new` [path-like] : path to file containing new locations to be added on the _main_ input file.
- `raster_file` [path-like] : path to the population raster file (GeoTIFF format).
- `do_update` [boolean] : if true, the script will read `location_new` and update the population table.
- `clipped_only` [boolean] : if false, the script extract population count from both clipped and un-clipped circular buffers.
- `versioning` [boolean] : if true, the script will save two CSV files 

The output files are kept in `geom/` and `out/` folders. Geopackage (GPKG) containing the buffers can be found in `geom/` while the population table (CSV) is kept in `out/`.

### Zonal Statistics Wrapper
`zonal_statistics.py` is a script to extract zonal statistics from raster input based on the list of features provided. Copy the script to the working directory to use it. Type `python zonal_statistics.py --help` to know how to use this script.

___
Contact: <rp1y21@soton.ac.uk>