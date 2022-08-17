import os
import sys
import numpy as np
import geopandas as gpd
import rasterio
from rasterio.merge import merge
from rasterio.mask import mask
from rasterio.plot import show
from shapely.geometry import Polygon

'''
Purpose: to merge some Dynamic World rasters and created one output
Author : Rhorom Priyatikanto, rp1y21@soton.ac.uk
'''

def usage():
    print('python dworld_wrapper.py -y year -b band(s)')
    print('                         -c shp_or_bounds(xmin,xmax,ymin,ymax)')
    print('                         -o filename')
    
def extraction(year, indexes, region, out_file):
    rasterdir = "Z:/Projects/WP000010_Covariates/Working/DynamicWorld/"
    tiles = gpd.read_file(rasterdir + 'index.shp')

    if type(region) == list:
        idx = tiles.geometry.intersects(region[0], align=False)
    else:
        idx = tiles.geometry.intersects(region, align=False)
    suffixes = tiles[idx].ID
    ntiles = np.sum(idx)
    if ntiles < 1:
        print('No intersection between tiles and clipping region')
        print('Is the clipping region contains land?')
        sys.exit(1)
        
    print('')
    print('Checking %d tiles'%ntiles)
    src_files_to_mosaic = []
    for suffix in suffixes:
        fname = '%s/dworld_%s_%s.tif'%(year, year, suffix)
        if (os.path.isfile(rasterdir + fname)):
            print(fname, 'available')
            src = rasterio.open(rasterdir + fname, 'r')
            src_files_to_mosaic.append(src)
        else:
            print(fname, 'not available')

    ntiles = len(src_files_to_mosaic)

    if ntiles < 1:
        print('Required tile(s) not available')
        sys.exit(1)
    
    if ntiles == 1:
        mosaic = src.read(indexes)
        out_trans = src.meta['transform']
        print('')
        print('Reading 1 tile')
    else:
        print('')
        print('Mosaicing %s tiles'%ntiles)
        mosaic, out_trans = merge(src_files_to_mosaic, indexes=indexes)

    out_meta = src.meta.copy()
    out_meta.update({"driver": "GTiff",
                     "height": mosaic.shape[1],
                     "width": mosaic.shape[2],
                     "count": len(indexes),
                     "transform": out_trans,
                     "crs": "EPSG:4326"
                    })
    with rasterio.open(out_file, 'w', **out_meta) as dest:
        dest.write(mosaic.astype('bool'))

    print('')
    print('Clipping raster')
    with rasterio.open(out_file, 'r') as src:
        clip, out_trans = rasterio.mask.mask(src, region, crop=True)
        out_meta = src.meta.copy()
    
    out_meta.update({"height": clip.shape[1],
                     "width": clip.shape[2],
                     "transform": out_trans,
                    })
    
    with rasterio.open(out_file, 'w', **out_meta) as dest:
        dest.write(clip.astype('bool'))

    print('')
    print('Extraction finished')

def main(argv=None):
    if argv == None:
        argv = sys.argv
    
    rasterdir = "Z:/Projects/WP000010_Covariates/Working/DynamicWorld/"
    
    if not(os.path.exists(rasterdir)):
        print('Check your access to the WorldPop Drive')
        print("//worldpop.files.soton.ac.uk/worldpop/")
        sys.exit(1)
        
    band_names = np.array(['water', 'trees', 'grass', 'flooded_vegetation', 'crops', 'shrub_and_scrub', 'built', 'bare', 'snow_and_ice'])
    region = []
    out_file = 'out_image.tif'
    i = 1
    
    while i < len(argv):
        if argv[i] == '-y':
            year = argv[i+1]
            if not(year in np.arange(2016,2022).astype(str)):
                print('Rasters from year %s is not available'%year)
                print('Available year: 2016-2021')
                sys.exit(1)
            
        elif argv[i] == '-b':
            band = argv[i+1]
            band = band.replace(' ','').split(',')
            if type(band) == str:
                band = [band]
                
            avail = [b in band_names for b in band]
            if np.sum(avail) < len(band):
                print('Check the band names:', band)
                print('Available bands: ', band_names)
                sys.exit(1)
                
            band_idx = [1+np.argwhere(band_names == b)[0][0] for b in band]
    
        elif argv[i] == '-c':
            clipper = argv[i+1]
            if clipper[-4:] == '.shp':
                if not(os.path.isfile(clipper)):
                    print('Clipper shapefile is not available')
                    sys.exit(1)
                    
                bound = gpd.read_file(clipper)
                if (bound._crs.srs != 'epsg:4326'):
                    print('Transforming CRS of the clipping region: from %s to epsg:4326'%(bound._crs.srs))
                    bound = bound.to_crs(4326)
                if len(bound) > 1:
                    print('The first of %d clipping regions is selected'%len(bound))
                region = bound.iloc[0].geometry
                
            else:
                try:
                    bound = np.array(clipper.replace(' ','').split(',')).astype(float)
                    region = Polygon(((bound[0],bound[2]), (bound[1],bound[2]),
                                      (bound[1],bound[3]), (bound[0],bound[3]),
                                      (bound[0],bound[2])))
                    region = [region] #gpd.GeoSeries(region, crs=4326)
                except:
                    print('The clipping boundary should be (xmin, xmax, ymin, ymax)')
                    sys.exit(1)

        elif argv[i] == '-o':
            out_file = argv[i+1]
            
        i += 1
        
    if len(region) < 1:
        usage()
        sys.exit(1)

    print('')
    print('Extracting Dynamic World rasters')
    print('year: %s, band(s): %s, output: %s'%(year, band, out_file))
    
    extraction(year, band_idx, region, out_file)
    
if __name__ == '__main__':
    sys.exit(main())
