#!/usr/bin/env python3

import sys
import ee
import pandas as pd
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
        print("✓ Earth Engine running...")

def getMuiltiSensorData(bbox, start_date, end_date,
                        grid_res=0.1, scale=500,
                        ndvi_thres=-0.02, elevation=True):
    region = ee.Geometry.Rectangle(bbox)
    start = ee.Date(start_date)
    end = ee.Date(end_date)

    # create a grid of sampling points over the bbox
    # resolution is given by `grid_res` in deg (0.05 = ~50km at equator)
    try:
        samples = region.coveringGrid('EPSG:4326', grid_res)
    #     .map(
    # lambda f: ee.Feature(f.geometry().centroid())
    # )
        n_samples = samples.size().getInfo()
    except Exception as err:
        print(f"Error creating grid:- {err}")
        return None
    else:
        print(f"{n_samples} samples created over {grid_res}° grid on bbox")

    


if __name__ == '__main__':
    startEarthEngine()

    df = getMuiltiSensorData(
        bbox = [5.00, 5.74, 6.66, 7.60],
        start_date= '2020-01-01',
        end_date= '2024-01-01'
    )