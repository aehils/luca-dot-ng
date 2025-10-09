#!/usr/bin/env python3

import sys
import ee
import geemap
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

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

def createGridPoints(bbox, grid_res=0.05):
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
    
    return points.tolist()

def getMuiltiSensorData(bbox, start_date, end_date,
                        grid_res=0.05, scale=500,
                        ndvi_thres=-0.02, include_elevation=True):
    region = ee.Geometry.Rectangle(bbox)
    start = ee.Date(start_date)
    end = ee.Date(end_date)

    # create a grid of sampling points over the bbox
    # resolution is given by `grid_res` in deg (0.05 = ~50km at equator)
    try:
        print("Building grid on bbox...")
        grid = createGridPoints(bbox, grid_res)
        features = [
            ee.Feature(ee.Geometry.Point(long,lat), {'id':i})
            for i, (long, lat) in enumerate(grid)
            ]
        samples = ee.FeatureCollection(features)
        
    except Exception as err:
        print(f"Error creating grid::- {err}")
        return None
    else:
        print(f"Sample Grid converted to Earth Engine FeatureCollection")
        # Verify the collection was created
        n_samples = samples.size().getInfo()
        print(f"{n_samples} samples ready.\n")

    # Dataset 1: MODIS NDVI (16-day, with quality filter)
    modis_ndvi = (ee.ImageCollection('MODIS/061/MOD13A1')
                  .filterDate(start, end)
                  .filter(ee.Filter.lt('SummaryQA', 2))  # Good quality pixels
                  .select(['NDVI', 'EVI']))
    
    # Dataset 2: MODIS Land Surface Temperature (8-day)
    modis_lst = (ee.ImageCollection('MODIS/061/MOD11A2')
                 .filterDate(start, end)
                 .select(['LST_Day_1km']))
    
    # Dataset 3: Precipitation (daily, then aggregate)
    precip = (ee.ImageCollection('UCSB-CHG/CHIRPS/DAILY')
              .filterDate(start, end)
              .select(['precipitation']))
    
    # Dataset 4: Sentinel-1 SAR (for forest structure)
    s1 = (ee.ImageCollection('COPERNICUS/S1_GRD')
          .filterBounds(region)
          .filterDate(start, end)
          .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV'))
          .filter(ee.Filter.eq('orbitProperties_pass', 'DESCENDING'))  # Consistent orbit
          .select(['VV', 'VH']))
    
    # Dataset 5: Hansen Forest Change (static baseline)
    hansen = ee.Image('UMD/hansen/global_forest_change_2023_v1_11')
    forest_2000 = hansen.select('treecover2000')
    forest_loss = hansen.select('loss')
    forest_gain = hansen.select('gain')
    loss_year = hansen.select('lossyear')  # For temporal labeling
    
    # Optional: Elevation (static)
    if include_elevation:
        elevation = ee.Image('USGS/SRTMGL1_003').select('elevation')
        
    
    


if __name__ == '__main__':
    startEarthEngine()

    df = getMuiltiSensorData(
        bbox = [5.00, 5.74, 6.66, 7.60],
        start_date= '2020-01-01',
        end_date= '2024-01-01'
    )