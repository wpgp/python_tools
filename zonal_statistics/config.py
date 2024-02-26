### CONFIGURATION ###
year_start = 2020
year_end = 2023
radii = [1,5]
location = 'sample/new_20240119.csv'
raster_file = '../pop/constrained/global_ppp_{year}_1km_UNadj_constrained.tif'
processing_mode = 'delete' #['new','add','delete','edit']
clipped_only = True
versioning = True
id_col = 'LOCATION_ID'

# raster_file defines the file naming format of the gridded 
# population data used in the process. Do not replace '{year}' 
# as this variable will be filled in get_population.py.

### END CONFIGURATION ###
