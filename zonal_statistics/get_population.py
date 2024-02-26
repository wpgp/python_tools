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
    area_large = zones[~small]['area'].values
    zones['pop'] = np.nan
    zones['cell_count'] = 0
    
    res = zonal_stats(zones[~small], raster_path, stats=['count'], add_stats={'pop':np.nansum})
    cnt_large = np.array([a['count'] for a in res])
    pop_large = np.array([a['pop'] for a in res])

    #ONLY DO SCALING WHEN THE PIXEL COUNT IS BIGGER THAN THE BUFFER AREA
    a = np.where(cnt_large > area_large)
    fac = np.ones(len(area_large))
    fac[a] = area_large[a]/cnt_large[a]
    pop_large = fac*np.array(pop_large)
    zones.loc[~small, 'pop'] = pop_large
    zones.loc[~small, 'cell_count'] = cnt_large

    if (small.sum() > 0):
        pts = gpd.points_from_xy(zones[small]['lon'], zones[small]['lat'], crs='epsg:4326')
        pop_small = point_query(pts, raster_path, interpolate=interpolate)
        pop_small = zones[small]['area'].values*np.array(pop_small, dtype=float)
        zones.loc[small, 'pop'] = pop_small
        zones.loc[small, 'cell_count'] = 1
    
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
            
            if processing_mode == 'new':
                param = {'input':location, 'rad':rad, 'output':'geom/buffer'}
            else:
                param = {'input':infile, 'rad':rad, 'output':'geom/buffer', 'id':id_col}
                param[processing_mode] = location
            if buffer_type == '_clipped':
                param['clip'] = True
            
            get_buffer.get_buffer(param)
            buffer = gpd.read_file(infile)
            #if not('remark' in buffer.columns.tolist()):
            #    buffer['remark'] = 'old'

            print('Processing:', outfile)
            if processing_mode == 'new':
                pop_df = pd.DataFrame(buffer).drop(columns=['geometry'])
            else:
                old_df = pd.read_csv(outfile)
                old_df['remark'] = 'old'
                if processing_mode == 'delete':
                    del_df = pd.read_csv(location)
                    sel = old_df[id_col].isin(del_df[id_col].values)
                    if len(sel) > 0:
                        old_df = old_df[~sel].reset_index(drop=True)                        

                buffer = buffer[buffer['remark'] == 'new']
                if (len(buffer) < 1):
                    if processing_mode == 'delete':
                        print(f'Deleting {np.sum(sel)} items')
                        print('Saving population table:', outfile)
                        old_df.to_csv(outfile, index=False)
                    if versioning:
                        today = date.today().strftime("%Y%m%d")
                        dated_outfile = f'{outfile[:-4]}_{today}.csv'
                        old_df.to_csv(dated_outfile, index=False)
                    continue
                pop_df = pd.DataFrame(buffer).drop(columns=['geometry'])

            print('Number of zones:', len(buffer))
            
            pop_df['remark'] = 'new'
            for year in range(year_start, year_end+1):
                pop_raster = raster_file.format(year=year)
                
                if not(os.path.isfile(pop_raster)):
                    print('Population raster cannot be found:', pop_raster)
                    sys.exit()
                
                print('Performing zonal statistics:', year)
                pop = get_population(buffer, pop_raster)
                pop_df[f'pop_{year}'] = pop['pop'].values
                pop_df['cell_count'] = pop['cell_count'].values
                
            if processing_mode != 'new':
                pop_df = pd.concat([old_df, pop_df], ignore_index=True)
                pop_df = pop_df.drop_duplicates(subset=[id_col], keep='last')

            print('Saving population table:', outfile)
            pop_df.to_csv(outfile, index=False)

            if versioning:
                today = date.today().strftime("%Y%m%d")
                dated_outfile = f'{outfile[:-4]}_{today}.csv'
                pop_df.to_csv(dated_outfile, index=False)

            print()
            
if __name__ == '__main__':
    sys.exit(main())