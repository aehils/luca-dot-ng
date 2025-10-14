#!/usr/bin/env python3

import sys
import ee
import geemap
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

from csv_exporting import df2csv
from  month_composite import compose
import process_data as p

def startEarthEngine():
    # authenticate Earth Engine and initialise API
    ee.Authenticate()
    try:
        ee.Initialize(project='sage-courier-474421-m9')
    except Exception as e:
        print(f"Could not start Earth Engine: {e}")
        sys.exit(1)
    else:
        print("\n✓ Earth Engine running :)\n")

def createGridPoints(bbox, grid_res=0.05, buffer_m=250):
    min_long, min_lat, max_long, max_lat = bbox
    longs = np.arange(min_long, max_long, grid_res)
    lats = np.arange(min_lat, max_lat, grid_res)
    
    # create meshgrid of longs and lats
    long_grid, lat_grid = np.meshgrid(longs, lats)
    # flatten to a list of long and lat pairs
    points = np.column_stack([long_grid.ravel(), lat_grid.ravel()])
    
    print(f"  Created {len(points)} grid points")
    print(f"  Grid: {len(longs)} cols x {len(lats)} rows")
    print(f"  Resolution: {grid_res}° (~{grid_res * 111:.1f} km at equator)\n")
    
    features = [
        ee.Feature(
            ee.Geometry.Point(longitude, latitude).buffer(buffer_m),
            {'id': i, 'long': longitude, 'lat': latitude}
        )
        for i, (longitude, latitude) in enumerate(points)
    ]

    return ee.FeatureCollection(features)

def getMultiSensorData(bbox, start_date, end_date,
                        grid_res=0.05, scale=500,
                        ndvi_thres=-0.02, include_elevation=True):
    region = ee.Geometry.Rectangle(bbox)
    start = ee.Date(start_date)
    end = ee.Date(end_date)

    # create a grid of sampling points over the bbox
    # resolution is given by `grid_res` in deg (0.05 = ~50km at equator)
    try:
        print("Building grid on bbox...")
        samples = createGridPoints(bbox, grid_res)
        
    except Exception as err:
        print(f"Error creating grid::- {err}")
        return None
    else:
        print(f"Sample Grid converted to Earth Engine FeatureCollection")

    
    # Convert to list and download
    data_points = compose(start_date, end_date, region, 
                          scale, include_elevation, samples)

    return data_points

if __name__ == '__main__':
    startEarthEngine()

    edo_bbox = [5.00, 5.74, 6.66, 7.60]


    try:
        raw_data_points = getMultiSensorData(
            edo_bbox,
            start_date= '2020-01-01',
            end_date= '2024-01-31'
        )
        raw_store = df2csv(raw_data_points, 
                           'test-a', 'data/edo_test')

    except Exception as e:
        print(f"Could not take data samples::- {e}")
    else:
        print("Samples collected successfully")

    featured_data_points = p.extract_features(
        raw_data_points)
    pathTo_featured_data_points = df2csv(
        featured_data_points,
        'test-b', 'data/edo_test')
    
    columns =['ndvi_mean', 'evi_mean', 'ndvi_min', 'ndvi_std', 
              'lst_mean_k', 'lst_std', 'precip_total_mm']
    try:
        # p.makeNumeric(featured_data_points)
        interpolated_points = p.temporal_interpolate(
            featured_data_points, columns)
        pathTo_interpolated_points = df2csv(
            interpolated_points,
            'test-c', 'data/edo_test')
    except Exception as e:
        print(f"Could not makeNumeric:: - {e}")

    # print("'Featured' points::::::::::::")
    # print(featured_data_points.info(), "\n")
    # print(featured_data_points.describe(), "\n")
    # print(featured_data_points.isnull().sum(), "\n")

    # print("FEATURED:: SOME FOREST LOSS AND TREE COVER INFO, VALUE COUNTS:::")
    # print(featured_data_points['forest_loss'].value_counts())
    # print(featured_data_points['tree_cover_2000'].value_counts(sort=False, ascending=True))
    
    print("DATA AFTER INTERPOLATION:::::::::::::")
    print(interpolated_points.info(), "\n")
    print(interpolated_points.describe(), "\n")
    print(interpolated_points.isnull().sum(), "\n")

    featured_data_points.hist(bins=50, figsize=(20,15))
    plt.show()






    
    


