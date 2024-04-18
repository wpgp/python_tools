### CONFIGURATION ###
year_start = 2021
year_end = 2021
radii = [10]
location = 'sample/points_1_edit.csv'
raster_file = '../../pop/global_ppp_{year}_1km_UNadj_constrained.tif'
processing_mode = 'edit'
clipped_only = True
versioning = True
id_col = 'LOCATION_ID'

# raster_file defines the file naming format of the gridded 
# population data used in the process. Do not replace '{year}' 
# as this variable will be filled in get_population.py.

### END CONFIGURATION ###
