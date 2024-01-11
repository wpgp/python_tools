print('Loading required packages')
import sys
import os
import numpy as np
import pandas as pd
import geopandas as gpd
from rasterstats import zonal_stats, point_query
from datetime import date

import get_buffer
from config import *

def usage():
    print('Description:')
    print('This script produces estimate of people impacted by conflicts at the listed')
    print('locations. The paths to the gridded population data and the location list are')
    print('defined in the config.py. Produced files are stored in geom/ and out/ folders.')
    print()
    print('Usage: python get_population.py')
    print()

def initialize():
    dirs = os.listdir()
    if not('out' in dirs):
        os.mkdir('out')
    if not('geom' in dirs):
        os.mkdir('geom')

def get_population(zones, raster_path, min_area=1, interpolate='nearest'):
    cols = zones.columns.values
    if not('area' in cols):
        zones['area'] = 1e-6*zones.geometry.to_crs(3857).area
    
    small = zones['area'] < min_area
    zones['pop'] = np.nan
    zones['cell_count'] = 0

    pts = gpd.points_from_xy(zones[small]['lon'], zones[small]['lat'], crs='epsg:4326')
    
    pop_small = point_query(pts, raster_path, interpolate=interpolate)

    res = zonal_stats(zones[~small], raster_path, stats=['count'], add_stats={'pop':np.nansum})
    cnt_large = np.array([a['count'] for a in res])
    pop_large = np.array([a['pop'] for a in res])

    fac = np.divide(zones[~small]['area'].values, cnt_large, where=(cnt_large>0))
    pop_small = zones[small]['area'].values*np.array(pop_small)
    pop_large = fac*np.array(pop_large)

    zones.loc[small, 'pop'] = pop_small
    zones.loc[~small, 'pop'] = pop_large

    zones.loc[small, 'cell_count'] = 1
    zones.loc[~small, 'cell_count'] = cnt_large
    return zones

def main():
    initialize()

    if clipped_only:
        buffer_types = ['_clipped']
    else:
        buffer_types = ['_clipped', '']

    for buffer_type in buffer_types:
        for rad in radii:
            infile = f'geom/buffer_{rad:.0f}km{buffer_type}.gpkg'
            outfile = f'out/pop_{rad:.0f}km{buffer_type}.csv'
            
            if do_update:
                param = {'input':infile, 'add':location_new, 'rad':rad, 'output':'geom/buffer', 'clip':(buffer_type=='_clipped')}
            else:
                param = {'input':location, 'rad':rad, 'output':'geom/buffer', 'clip':(buffer_type=='_clipped')}
            
            get_buffer.get_buffer(param)
            buffer = gpd.read_file(infile)

            if do_update:
                old_df = pd.read_csv(outfile)
                old_df['remark'] = 'old'
                buffer = buffer[buffer['remark'] == 'new']
                if (len(buffer) < 1):
                    print('New data is not found. No update is performed.')
                    return
                pop_df = pd.DataFrame(buffer).drop(columns=['geometry'])
            else:
                pop_df = pd.DataFrame(buffer).drop(columns=['geometry'])
            
            pop_df['remark'] = 'new'
            for year in range(year_start, year_end+1):
                pop_raster = raster_file.format(year=year)
                
                if not(os.path.isfile(pop_raster)):
                    print('Population raster cannot be found:', pop_raster)
                    sys.exit()
                
                pop = get_population(buffer, pop_raster)
                pop_df[f'pop_{year}'] = pop['pop'].values
                pop_df['cell_count'] = pop['cell_count'].values
                
            if do_update:
                pop_df = pd.concat([old_df, pop_df], ignore_index=True)

            print('Saving population table')
            pop_df.to_csv(outfile, index=False)

            if versioning:
                today = date.today().strftime("%Y%m%d")
                dated_outfile = f'{outfile[:-4]}_{today}.csv'
                pop_df.to_csv(dated_outfile, index=False)

            print()
            
if __name__ == '__main__':
    sys.exit(main())