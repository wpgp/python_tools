import os
import sys
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
import matplotlib.pyplot as plt
from rasterstats import zonal_stats

def usage():
    print('python zonal_statistics.py -f raster_file -z zones -r buffer_radii')
    print('                           -s statistics -b band_num')
    print('                           -p -o output_file')
    
def main(argv=None):
    if argv == None:
        argv = sys.argv
    
    create_buffer = False
    cnt = 1
    band_indexes = [1]
    output_file = 'output.csv'
    do_plot = False
    stats = ['min','max','mean','std']

    i = 1
    while i < len(argv):
        if (argv[i] == '-f'):
            raster_file = argv[i+1]
            if not(os.path.isfile(raster_file)):
                print('Raster file is not found')
                sys.exit(1)
            with rasterio.open(raster_file, 'r') as src:
                crs = src.crs.to_string()
                cnt = src.meta['count']
            band_indexes = np.arange(1, cnt+1)
                
        elif (argv[i] == '-z'):
            zones_file = argv[i+1]
            if not(os.path.isfile(zones_file)):
                print('Zone shapefile is not found')
                sys.exit(1)

            if (zones_file[-4:] == '.shp'):
                gdf = gpd.read_file(zones_file)
                crs2 = gdf._crs.srs.upper()
                if (crs2 != crs):
                    print('Transforming CRS of the zones: from %s to %s'%(crs2, crs))
                    gdf = gdf.to_crs(crs)
                if (gdf.geometry[0].geometryType() == 'Point'):
                    create_buffer = True
                else:
                    create_buffer = False
                    gdf.to_file('tmp_zones.shp', index=False)

            elif (zones_file[-4:] == '.csv'):
                gdf = pd.read_csv(zones_file)
                if not('lon' in gdf.columns):
                    print('lon column is not found in %s'%zones_file)
                    sys.exit(1)
                if not('lat' in gdf.columns):
                    print('lat column is not found in %s'%zones_file)
                    sys.exit(1)
                    
                pts = gpd.GeoSeries([Point(x,y) for x,y in zip(gdf.lon.values,gdf.lat.values)])
                gdf['geometry'] = pts
                create_buffer = True
                
        elif (argv[i] == '-r'):
            buffer = argv[i+1].replace(' ','').split(',')
            if (isinstance(buffer,str)):
                buffer = [buffer]
            buffer = np.array(buffer, dtype=float)
            #if (crs[5:] in ['4326']):
            #    buffer *= 8.983346e-6 #converting metre to degrees
            if (create_buffer):
                gdf2 = gpd.GeoDataFrame()
                #if there are multiple buffer radii, than additional rows
                #will be created
                for j,b in enumerate(buffer):
                    df = gdf.copy()
                    df['geometry'] = gdf.to_crs(3857).buffer(b)
                    df['buffer'] = b
                    df['buff_idx'] = j
                    gdf2 = pd.concat([gdf2,df], ignore_index=False)
                gdf2.to_crs(crs).to_file('tmp_zones.shp', index=False)
                    
        elif (argv[i] == '-b'):
            band_indexes = argv[i+1].replace(' ','').split(',')
            if (isinstance(band_indexes,str)):
                band_indexes = [band_indexes]
            band_indexes = np.array(band_indexes, dtype=int)
            
        elif (argv[i] == '-o'):
            output_file = argv[i+1]
            
        elif (argv[i] == '-p'):
            do_plot = True
        
        elif (argv[i] == '-s'):
            stats = argv[i+1].replace(' ','').split(',')
            if (isinstance(stats,str)):
                stats = [stats]
                
        i += 1
        
    if create_buffer:
        remark = '%d points, %d buffer(s)'%(len(gdf), len(buffer))
    else:
        remark = '%d polygons'%(len(gdf))
        
    output_files = ['band%d_'%b+output_file for b in band_indexes]
    
    print('')
    print('Performing zonal statistics')
    print('raster: %s (%d bands), zones: %s'%(raster_file, cnt, remark))
    print('output:', output_files)
    print('stats:', stats)

    for band_num in band_indexes:
        stat = zonal_stats('tmp_zones.shp', raster_file, nodata=-99, stats=stats, band_num=int(band_num))
        stat = pd.DataFrame(stat)
        gdf = gpd.read_file('tmp_zones.shp')
        for s in stat.columns:
            gdf[s] = stat[s].values
        if (output_file[-4:] == '.shp'):
            gdf.to_file('band%d_'%(band_num) + output_file, index=False)
        if (output_file[-4:] == '.csv'):
            df = pd.DataFrame(gdf).drop(columns=['geometry'])
            df.to_csv('band%d_'%(band_num) + output_file, index=False)
            
        if do_plot:
            print('Plotting...')
            print('Close the plotting window to continue')
            gdf.plot(column=stats[0], cmap='jet', alpha=0.2)
            plt.tight_layout()
            plt.savefig('band%d_plot.png'%(band_num))
            plt.show()
            
        print('Done with band', band_num)
    
    os.remove('tmp_zones.shp')
    
if __name__ == '__main__':
    sys.exit(main())