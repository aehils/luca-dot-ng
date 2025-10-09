#!/usr/bin/env python3

import sys
import ee
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
                        ndvi_thres=-0.02, elevation=True):
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
        print(f"Sample Grid converted to Earth Engine FeatureCollection")
        
        # Verify the collection was created
        n_samples = samples.size().getInfo()
        print(f"{n_samples} samples ready.\n")
        return samples
        
    except Exception as err:
        print(f"Error creating grid::- {err}")
        return None

    


if __name__ == '__main__':
    startEarthEngine()

    df = getMuiltiSensorData(
        bbox = [5.00, 5.74, 6.66, 7.60],
        start_date= '2020-01-01',
        end_date= '2024-01-01'
    )