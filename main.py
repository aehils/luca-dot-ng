#!/usr/bin/env python3

import sys
import ee
import geemap
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

from pandas.plotting import scatter_matrix
from datetime import datetime, timedelta
from sklearn.model_selection import StratifiedShuffleSplit

from file_handling import df2csv
from  month_composite import compose
from process_data import Dataset
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

    # get mulltiSensor data commented out to reduce 
    #  computational overload during testsing
    #  will instead...
    raw_data = pd.read_csv('data/edo_test/test-a.csv')
    # try:
    #     raw_data = getMultiSensorData(
    #         edo_bbox,
    #         start_date= '2020-01-01',
    #         end_date= '2024-01-31'
    #     )
    #     pathTo_raw_data = df2csv(raw_data_points, 
    #                        'test-a', 'data/edo_test')
    # except Exception as e:
    #     print(f"Could not take data samples::::: \n {e}")
    # else:
    # print("Samples collected successfully")

    # categorise forest_loss by quartiles using pd.qcut
    raw_data['loss_cat_q'] = pd.qcut(raw_data['forest_loss'], 
                                     q=5, 
                                     duplicates='drop')
    # raw_data['loss_cat_q'] = raw_data['loss_cat_q'].cat.codes + 1

    # here im splitting off a portion of the data for testing later
        # but because the data is skewed, i want to make sure the split
        # is representative of the popution, so stratified split
    split = StratifiedShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    for train_idx, test_idx in split.split(raw_data, raw_data['loss_cat_q']):
        strat_trainingSet = raw_data.loc[train_idx]
        strat_testingSet = raw_data.loc[test_idx]
    for set_ in (strat_trainingSet, strat_testingSet):
        set_.drop('loss_cat_q', axis=1, inplace=True)

    forest = Dataset(strat_trainingSet.copy())
    forest_csv = df2csv(forest.df,
                        'forest', './data')
    
    columns =['ndvi', 'evi', 'ndvi_std', 
              'lst_k', 'lst_std', 'precip_total_mm']
    
    forest.newFeatures()
    
    forest2 = df2csv(forest.df,
                     'forest2', './data')
    # .temporal_interpolate(columns=columns).tidy()

    # look for correlation
    non_numeric_cols = ['date', 'months_until_loss', 'loss_year']
    forest_n = forest.df.drop(columns=non_numeric_cols)
    
    corr_matrix = forest_n.corr()
    print(corr_matrix["forest_loss"].sort_values(ascending=False), "\n\n")

    plt.show()

    
    
    print(forest.df.info(), "\n")
    print(forest.df.isnull().sum(), "\n")

    q = df2csv(strat_testingSet,
               'stat_test', './data')