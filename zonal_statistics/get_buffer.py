import sys
import os
import numpy as np
import pandas as pd
import geopandas as gpd
from scipy.spatial import Voronoi
from shapely.geometry import LineString
from shapely.ops import polygonize, linemerge, unary_union

import warnings
warnings.filterwarnings("ignore")

def usage():
    print('Usage: python get_buffer.py -f path.csv -r 1000 [OPTIONS]')
    print('Options:')
    print('-i, --input       [required] Path to the input file')
    print('-a, --add                    Path to the file containing additional points')
    print('                             In this mode, additional buffers will be concatenated')
    print('                             to the existing geopackages (the input file).')
    print('-r, --rad                    Radius of the buffer in kilometer. Default value: 5')
    print('-o, --output                 Prefix name. Default value: output')
    print('-c, --clip                   Perform clipping to overlapping buffers. ')
    print('-h, --help                   Show this message and exit.')
    print('')
    print('Example: python get_buffer.py -f sample/points_1.csv -a sample/points_2.csv')
    print('                              -r 10 -o buffer -clip')
    print()

def get_input(path_, rad_=5000):
    # Read input CSV or Excel containing coordinates of the locations.
    # [lat, latitude, y] can be regarded as latitude column.
    # [lon, long, longitude, x] can be regarded as longitude column.
    # The column naming is case insensitive.
    # This function produce geopandas dataframe containg circular buffers
    # as the geometry. The point location (lon, lat) is kept and the area
    # of the buffer is added.

    if not(os.path.isfile(path_)):
        print('Input file is not found:', path_)
        sys.exit(1)
    
    ext = path_.split('.')[-1]
    print('Reading input file')

    if (ext in ['csv', 'CSV', 'xls', 'XLS', 'xlsx', 'XLSX']):
        if (ext in ['csv', 'CSV']):
            df = pd.read_csv(path_)
        else:
            df = pd.read_excel(path_)
    
        cols = df.columns.values
        lat = [c if c.lower() in ['lat','latitude','y'] else 'NA' for c in cols]
        lat = list(filter(('NA').__ne__, lat))[0]
        
        lon = [c if c.lower() in ['lon','long','longitude','x'] else 'NA' for c in cols]
        lon = list(filter(('NA').__ne__, lon))[0]
        
        gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df[lon], df[lat]), crs='epsg:4326')
        buf = gdf.to_crs(3857).buffer(rad_)
        gdf = gdf.drop(columns=[lon,lat])
        gdf['area'] = 1e-6*buf.area
        gdf['lon'] = gdf.geometry.x
        gdf['lat'] = gdf.geometry.y
        gdf['geometry'] = buf.to_crs(4326)
        
    elif (ext in ['gpkg', 'GPKG', 'shp', 'SHP', 'geojson', 'json']):
        gdf = gpd.read_file(path_)
        crs = gdf.crs.srs
        if (crs != 'epsg:4326'):
            print(f'Update CRS from {crs} to epsg:4326')
            gdf = gdf.to_crs(4326)
            
        geom_type = str(gdf.geometry.values[0])[0:5]
        if (geom_type == 'POINT'):
            print('Creating buffer around points')
            buf = gdf.to_crs(3857).buffer(rad_)

            cols = gdf.columns.values
            lat = [c if c.lower() in ['lat','latitude','y'] else 'NA' for c in cols]
            lat = list(filter(('NA').__ne__, lat))[0]
            
            lon = [c if c.lower() in ['lon','long','longitude','x'] else 'NA' for c in cols]
            lon = list(filter(('NA').__ne__, lon))[0]

            gdf = gdf.drop(columns=[lon,lat])
            gdf['area'] = 1e-6*buf.area
            gdf['lon'] = gdf.geometry.x
            gdf['lat'] = gdf.geometry.y
            gdf['geometry'] = buf.to_crs(4326)
        
    return gdf

def get_voronoi(gdf_):
    # This function creates voronoi tasselations based on the
    # points provided in the input geodataframe. 
    # This geodataframe should contain (lon, lat) of each 
    # point/centroid.

    vor = None
    print('Creating Voronoi diagram')
    b = gdf_.bounds.describe()
    cx = gdf_['lon']
    cy = gdf_['lat']
    
    x1,y1 = b.loc['min','minx']-10, b.loc['min','miny']-10
    x2,y2 = b.loc['max','maxx']+10, b.loc['max','maxy']+10
    bounds = [(x1,y1),(x2,y1),(x2,y2),(x1,y2),(x1,y1)]
    coords = np.concatenate((np.stack([cx.tolist(), cy.tolist()], axis=1), bounds))
    v = Voronoi(coords)
    lines = [LineString(v.vertices[line]) for line in 
             v.ridge_vertices if -1 not in line]
    vor = gpd.GeoDataFrame(geometry=lines)
    return vor

def non_overlaps(geom, line):
    # Clipping geometry (geom) with lines (line)
    # where the original centroid is inside the
    # clipped geometry.

    line.append(geom.boundary)
    centroid = geom.centroid
    merged = linemerge(line)
    borders = unary_union(merged)
    polygons = np.array(list(polygonize(borders)))
    is_inside = [centroid.within(g) for g in polygons]
    
    return polygons[is_inside][0]

def get_buffer(argv=None):
    infile = 'input'
    addfile = None
    rad = 5
    outfile = 'output'
    clip = False

    if argv is None:
        argv = sys.argv
        if len(argv) < 3:
            sys.exit(usage())
        iter = range(len(argv))
        vals = argv
        suf = 1
        pre = ''
    else:
        iter = list(argv.keys())
        vals = {i:'--'+i for i in iter}
        suf = ''

    for i in iter:
        arg = vals[i]
        if (arg in ['-i', '--input']):
            infile = argv[i+suf]
            if not(os.path.isfile(infile)):
                print('Input file is not found:', infile)
                sys.exit(1)
        elif(arg in ['-a', '--add']):
            addfile = argv[i+suf]
            if not(os.path.isfile(addfile)):
                print('Additional file is not found:', addfile)
                sys.exit(1)
        elif(arg in ['-r', '--rad']):
            rad = float(argv[i+suf])
        elif(arg in ['-o', '--output']):
            outfile = argv[i+suf]
        elif(arg in ['-c', '--clip']):
            clip = True
        elif(arg in ['-h', '--help']):
            usage()
            sys.exit(1)

    gdf0 = get_input(infile, rad_=1000*rad)
    gdf0['remark'] = 'old'
    pts  = gdf0.copy()
    
    if addfile:
        # Updating the old buffer by adding new items from
        # the additional file. The buffers affected by this 
        # addition will be re-clipped.

        gdf1 = get_input(addfile, rad_=1000*rad)
        gdf1['remark'] = 'new'
        if clip:
            pts = pd.concat([gdf0, gdf1], ignore_index=True).reset_index(drop=True)
            vor = get_voronoi(pts)
            print('Clipping additional buffers')
            for i,row in gdf1.iterrows():
                b0 = row['geometry'].bounds
                g1 = vor.cx[b0[0]:b0[2], b0[1]:b0[3]]
                if (len(g1) > 0):
                    non = non_overlaps(row.geometry, g1.geometry.tolist())
                    gdf1.loc[i,'geometry'] = non

                g2 = gdf0.cx[b0[0]:b0[2], b0[1]:b0[3]]
                n2 = len(g2)
                for j,item in g2.iterrows():
                    b0 = item['geometry'].bounds
                    g1 = vor.cx[b0[0]:b0[2], b0[1]:b0[3]]
                    if len(g1) > 0:
                        non = non_overlaps(item.geometry, g1.geometry.tolist())
                        gdf0.loc[j,'geometry'] = non
                        gdf0.loc[j,'remark'] = 'new'
            
        gdf0 = pd.concat([gdf0, gdf1], ignore_index=True).reset_index(drop=True)
        
    elif clip:
        # Perform clipping to the buffers to avoid overlaps.
        
        vor = get_voronoi(pts)
        print('Clipping buffers')
        for i,row in gdf0.iterrows():
            b0 = row['geometry'].bounds
            g1 = vor.cx[b0[0]:b0[2], b0[1]:b0[3]]
            if (len(g1) > 0):
                non = non_overlaps(row.geometry, g1.geometry.tolist())
                gdf0.loc[i,'geometry'] = non
        gdf0['remark'] = 'new'

    suffix = ''
    if clip:
        suffix = '_clipped'
        
    gdf0['area'] = 1e-6*gdf0.to_crs(3857).area
    print('Saving geometry file')    
    gdf0.to_file(f'{outfile}_{rad:.0f}km{suffix}.gpkg', index=False)
    
if __name__ == '__main__':
    sys.exit(get_buffer())