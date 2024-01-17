### CONFIGURATION ###
year_start = 2023
year_end = 2023
radii = [1,2,5]
location = 'geom/buffer_5km_clipped.gpkg'
location_new = 'sample/points_2.csv'
raster_file = '../../ACLED/data/global_ppp_{year}_1km_UNadj_constrained.tif'
do_update = True
clipped_only = True
versioning = True

# raster_file defines the file naming format of the gridded 
# population data used in the process. Do not replace '{year}' 
# as this variable will be filled in get_population.py.

### END CONFIGURATION ###