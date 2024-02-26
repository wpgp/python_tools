import sys
import os
import numpy as np
import pandas as pd
import geopandas as gpd
import fiona
from tqdm import tqdm
from scipy.spatial import Voronoi
from shapely.geometry import LineString
from shapely.ops import polygonize, linemerge, unary_union

import warnings
warnings.filterwarnings("ignore")

def usage():
    print('Usage: python get_buffer.py -i path.csv -r 1000 [OPTIONS]')
    print('Options:')
    print('-i, --input       [required] Path to the input file')
    print('-a, --add                    Path to the file containing additional points')
    print('                             In this mode, additional buffers will be concatenated')
    print('                             to the existing geopackages (the input file).')
    print('-d, --delete                 Path to the file containing IDs to be removed')
    print('                             from the existing geopackages (the input file).')
    print('-e, --edit                   Path to the file containing IDs of the points to')
    print('                             be edited. New coordinates of the points should')
    print('                             be provided (lon-lat columns).')
    print('-r, --rad                    Radius of the buffer in kilometer. Default value: 5')
    print('-o, --output                 Prefix name. Default value: output')
    print('-c, --clip                   Perform clipping to overlapping buffers. ')
    print('--id                         ID column name')
    print('-h, --help                   Show this message and exit.')
    print('')
    print('Example: python get_buffer.py -i sample/points_1.csv -a sample/points_2.csv')
    print('                              -r 10 -o buffer -clip')
    print()

def buffer_from_points(x, y, r, as_gdf=False):
    geom = gpd.points_from_xy(x, y, crs=4326).to_crs(3857).buffer(r).to_crs(4326)
    if as_gdf:
        geom = gpd.GeoDataFrame(geometry=geom)
    return geom

def get_input(path_, rad_=5000):
    # Read input CSV or Excel containing coordinates of the locations.
    # [lat, latitude, y] can be regarded as latitude column.
    # [lon, long, longitude, x] can be regarded as longitude column.
    # The column naming is case insensitive.
    # This function produce geopandas dataframe containg circular buffers
    # as the geometry. The point location (lon, lat) is kept and the area
    # of the buffer is added.

    print('Radius (m):', rad_)
    if not(os.path.isfile(path_)):
        print('Input file is not found:', path_)
        sys.exit(1)
    
    ext = path_.split('.')[-1]
    print('Reading input file:', path_)

    if (ext in ['csv', 'CSV', 'xls', 'XLS', 'xlsx', 'XLSX']):
        if (ext in ['csv', 'CSV']):
            df = pd.read_csv(path_).dropna()
        else:
            df = pd.read_excel(path_).dropna()
    
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
        layer = ''
        
    elif (ext in ['gpkg', 'GPKG', 'shp', 'SHP', 'geojson', 'json']):
        layer = fiona.listlayers(path_)[0]
        gdf = gpd.read_file(path_)
        crs = gdf.crs.srs
        if not(crs in ['epsg:4326', 'EPSG:4326']):
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
        
    return gdf, layer

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

def add_rows(gdf0, gdf1, clip=True, col='LOCATION_ID'):
    # Updating the old buffer by adding new items from
    # the additional file. The buffers affected by this 
    # addition will be re-clipped.
    gdf1['remark'] = 'new'
    print(f'Add {len(gdf1)} items to the old buffers')
    if clip:
        pts = pd.concat([gdf0, gdf1], ignore_index=True).reset_index(drop=True)
        vor = get_voronoi(pts)
        print(f'Clipping additional buffers: {len(gdf1)}++')
        for i,row in tqdm(gdf1.iterrows(), total=gdf1.shape[0]):
            b0 = row['geometry'].bounds
            g1 = vor.cx[b0[0]:b0[2], b0[1]:b0[3]]
            if (len(g1) > 0):
                non = non_overlaps(row.geometry, g1.geometry.tolist())
                gdf1.loc[i,'geometry'] = non

            g2 = gdf0.cx[b0[0]:b0[2], b0[1]:b0[3]]
            for j,item in g2.iterrows():
                b0 = item['geometry'].bounds
                g1 = vor.cx[b0[0]:b0[2], b0[1]:b0[3]]
                if len(g1) > 0:
                    non = non_overlaps(item.geometry, g1.geometry.tolist())
                    gdf0.loc[j,'geometry'] = non
                    gdf0.loc[j,'remark'] = 'new'
        
    gdf0 = pd.concat([gdf0, gdf1], ignore_index=True).reset_index(drop=True)
    gdf0 = gdf0.drop_duplicates(subset=[col], keep='last')
    gdf0 = gpd.GeoDataFrame(gdf0, geometry='geometry')

    return gdf0

def del_rows(gdf0, gdf1, clip=True, col='LOCATION_ID', rad=5000):
    # Deleting selected rows from the old buffer
    # based on the IDs listed in the secondary input file. 
    # The buffers affected by this process will be re-clipped.

    sel = gdf0[col].isin(gdf1[col].values)
    nsel = np.sum(sel)
    if nsel < 1:
        print(f'{col} for deletion is not in the old buffers')
        return gdf0
    
    rem = gdf0[sel].copy()
    gdf0 = gdf0[~sel].reset_index(drop=True)
    vor0 = get_voronoi(gdf0)
    print(f'Delete {np.sum(sel)} items from the old buffers')

    if clip:
        old_buf = buffer_from_points(gdf0.lon, gdf0.lat, rad, as_gdf=True)
        rem_buf = buffer_from_points(rem.lon, rem.lat, rad, as_gdf=False)
        print(f'Check affected buffers for re-clipping')
        for buf in tqdm(rem_buf):
            b0 = buf.bounds
            g2 = old_buf.cx[b0[0]:b0[2], b0[1]:b0[3]]
            for j,item in g2.iterrows():
                b2 = item['geometry'].bounds
                g1 = vor0.cx[b2[0]:b2[2], b2[1]:b2[3]]
                if len(g1) > 0:
                    non = non_overlaps(item.geometry, g1.geometry.tolist())
                    gdf0.loc[j,'geometry'] = non
                    gdf0.loc[j,'remark'] = 'new'
        
    return gdf0

def get_buffer(argv=None):
    infile = 'input'
    addfile = None
    delfile = None
    edtfile = None
    rad = 5
    id_col = 'LOCATION_ID'
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
        elif(arg in ['-d', '--delete']):
            delfile = argv[i+suf]
            if not(os.path.isfile(delfile)):
                print('Input file for deletion is not found:', delfile)
                sys.exit(1)
        elif(arg in ['-e', '--edit']):
            edtfile = argv[i+suf]
            if not(os.path.isfile(edtfile)):
                print('Input file for edit is not found:', edtfile)
                sys.exit(1)
        elif(arg in ['--id']):
            id_col = argv[i+suf]
        elif(arg in ['-r', '--rad']):
            rad = float(argv[i+suf])
        elif(arg in ['-o', '--output']):
            outfile = argv[i+suf]
        elif(arg in ['-c', '--clip']):
            clip = True
        elif(arg in ['-h', '--help']):
            usage()
            sys.exit(1)

    gd0, layer = get_input(infile, rad_=1000*rad)
    gd0['remark'] = 'old'
    pts  = gd0.copy()
    
    if addfile:
        # Updating the old buffer by adding new items from
        # the additional file. The buffers affected by this 
        # addition will be re-clipped.
        gd1, _ = get_input(addfile, rad_=1000*rad)
        gd1.to_file('tmp.gpkg')
        gd0 = add_rows(gd0, gd1, clip=clip, col=id_col)
    elif delfile:
        # Updating the old buffer by deleting items listed in
        # the secondary input file. The buffers affected by this 
        # process will be re-clipped.
        gd1 = pd.read_csv(delfile)
        gd0 = del_rows(gd0, gd1, clip=clip, col=id_col, rad=1000*rad)
    elif edtfile:
        # Updating the coordinates of the items listed in
        # the secondary input file. The buffers affected by this 
        # process will be re-clipped.
        gd1, _ = get_input(edtfile, rad_=1000*rad)
        gd0 = del_rows(gd0, gd1, clip=clip, col=id_col, rad=1000*rad)
        gd0 = add_rows(gd0, gd1, clip=clip, col=id_col)
    elif clip:
        # Perform clipping to the buffers to avoid overlaps.        
        vor = get_voronoi(pts)
        print(f'Clipping buffers: {len(gd0)}')
        for i,row in tqdm(gd0.iterrows(), total=gd0.shape[0]):
            b0 = row['geometry'].bounds
            g1 = vor.cx[b0[0]:b0[2], b0[1]:b0[3]]
            if (len(g1) > 0):
                non = non_overlaps(row.geometry, g1.geometry.tolist())
                gd0.loc[i,'geometry'] = non
        gd0['remark'] = 'new'

    suffix = ''
    if clip:
        suffix = '_clipped'
        
    new_items = np.sum(gd0['remark'] == 'new')
    print('Processed buffers:')
    print('Old:', np.sum(gd0['remark'] == 'old'))
    print('New:', new_items)

    gd0 = gd0.reset_index(drop=True)
    gd0['area'] = 1e-6*gd0.to_crs(3857).area
    if new_items > 0:
        print('Saving geometry file')    
        gd0.to_file(f'{outfile}_{rad:.0f}km{suffix}.gpkg', index=False, 
                    mode='w', driver='GPKG', layer=layer)
    
if __name__ == '__main__':
    sys.exit(get_buffer())
