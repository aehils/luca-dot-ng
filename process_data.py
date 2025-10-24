import sys
import pandas as pd
import numpy as np
from scipy.spatial import cKDTree, distance
from scipy.spatial import distance


def clean_data(df):

    # if 'forest_loss' in df.columns:
    #     df['forest_loss'] = (df['forest_loss'] > 0).astype(int)
    #     if 'loss_year' in df.columns:
    #         df['forest_loss'] = (df['loss_year'] > 0).astype(int)
    
    if 'loss_year' in df.columns:
    # Calculate months until loss (positive = before, negative = after, None = no loss)
        df['months_until_loss'] = df.apply(
            lambda row: ((2000 + row['loss_year']) - row['year']) * 12 + (12 - row['month'])
            if row['loss_year'] > 0 else None,
            axis=1
        )

    if 'months_until_loss' in df.columns:
    # Use loc to conditionally set values
        df.loc[(df['forest_loss'] == 0), 
               ['months_until_loss', 'loss_year']] = "No Loss"
        df['months_until_loss'] = df['months_until_loss'].astype(object)
        df['loss_year'] = df['loss_year'].astype(object)
    
    if 'sar_vv' in df.columns and 'sar_vh' in df.columns:
        df = df.dropna(subset=['sar_vv', 'sar_vh'])

    # filter rows where there was no tree cover
    df = df[df['tree_cover_2000'] != 0]

    #  clip the value range of ndvi and evi between 0 and 1
    df['ndvi'] = df['ndvi'].clip(0, 1)
    df['evi'] = df['evi'].clip(0, 1)

    return df

def assert_types(df):

    def makeNumeric(df):
        exceptions = ['lat', 'long', 'date', 'months_until_loss', 'loss_year']

        # Convert all other columns to numeric
        for col in df.columns:
            if col not in exceptions:
                df[col] = pd.to_numeric(df[col], errors='coerce')
    makeNumeric(df)
    df['date'] = pd.to_datetime(df['date'])


def temporal_interpolate(df, columns):
    
# Function to fill missing with mean from other years (same month, same id)
    def fill_with_yearly_mean(group, col):
        # Group by month to get seasonal means across years
        monthly_means = group.groupby('month')[col].mean()
        
        # For each row, if null, fill with the mean for that month
        def fill_row(row):
            if pd.isnull(row[col]):
                return monthly_means.get(row['month'], np.nan)  # Fallback to NaN if no other data
            return row[col]
        
        group[col] = group.apply(fill_row, axis=1)
        return group

    # Apply to each id group for specific columns
    for col in columns:
        group = df.groupby('id', group_keys=False)
        df = group.apply(
            lambda g: fill_with_yearly_mean(g, col), 
            include_groups=True).reset_index(drop=True)
    
    # FIXED: Add fallback linear interpolation for remaining (sort by date first)
    df = df.sort_values(['id', 'date'])
    for col in columns:
        df[col] = df.groupby('id')[col].transform(
            lambda x: x.interpolate(method='linear', limit_direction='both')
        )
    
    # FIXED: Final ffill/bfill for any edge/all-NaN cases
    for col in columns:
        df[col] = df.groupby('id')[col].transform(lambda x: x.ffill().bfill())

    df = df.dropna()

    print("DATA AFTER INTERPOLATION:::::::::::::")
    print(df.info(), "\n")
    print(df.describe(), "\n")
    print(df.isnull().sum(), "\n")
    return df

def extract_features(df):

    #  Lags and Deltas

    #  combine ndvi, evi and forest health into a
    if 'ndvi' in df.columns:
        df['ndvi_delta'] = df['ndvi'] - (df.groupby('id')['ndvi'].shift(1))

        df['ndvi_roll_mean_3m'] = (
            df.groupby('id')['ndvi']
            .rolling(window=3, min_periods=1)
            .mean()
            .reset_index(0, drop=True)
            )
        

    if 'precip_total_mm' in df.columns:
        df['precip_lag1'] = df.groupby('id')['precip_total_mm'].shift(1)
        df['precip_delta'] = df['precip_total_mm'] - df['precip_lag1']
        # also computing an index for dryness, rainfall against temp
        df['dryness'] = df.apply(
        lambda row: row['precip_total_mm'] / row['lst_k'] if row['lst_k'] > 0 else 0,
        axis=1
    )
    
    # compute new feature: forest_health
    df['forest_health'] = (0.5 * df['ndvi'] + 
                           0.5 * df['evi']) * (df['tree_cover_2000'] / 100)

    # forest structure derived from ratio of sar_vh to sar_vv
    if 'sar_vv' and 'sar_vh' in df.columns:
        df['sar_vh_vv_ratio'] = df['sar_vh'] / df['sar_vv']

    try:
        #  spatial proximity to forest loss
        df = compute_dist_to_prev_loss(df)
    except Exception as err:
        print(f"Cannot build tree::- {err}")
        df['dist_to_loss'] = np.nan
    else:
        df = df.dropna()

    return df
        

def compute_dist_to_prev_loss(df):
    # Ensure data sorted by time
    df = df.sort_values(by=['year', 'month']).reset_index(drop=True)

    dist_values = []
    prev_loss_points = np.empty((0, 2))  # stores lat/long of previous losses

    for _, row in df.iterrows():
        if len(prev_loss_points) > 0:
            # compute distance to *past* loss points only
            dist = np.min(distance.cdist([[row['lat'], row['long']]], prev_loss_points))
        else:
            dist = np.nan

        dist_values.append(dist)

        # if this record itself is a forest loss, add it to memory for future points
        if row['forest_loss'] == 1:
            prev_loss_points = np.vstack([prev_loss_points, [row['lat'], row['long']]])

    df['dist_to_prev_loss'] = dist_values
    return df
