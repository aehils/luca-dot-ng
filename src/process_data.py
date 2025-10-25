import sys
import pandas as pd
import numpy as np
from scipy.spatial import cKDTree, distance
from scipy.spatial import distance

class Dataset():

    def __init__(self, data, get=None):
        if get:
            data = pd.read_csv(get)
        self.df = data

    def tidy(self):

        self.df['ndvi'] = self.df['ndvi'].clip(0, 1)
        self.df['evi'] = self.df['evi'].clip(0, 1)

        # filter out rows where tree cover was 0; non-zero only
        self.df = self.df[self.df['tree_cover_2000'] != 0]

        # similarly, drop rows where sar_vv or sar_vh is nan
        if 'sar_vv' in self.df.columns and 'sar_vh' in self.df.columns:
            self.df = self.df.dropna(subset=['sar_vv', 'sar_vh'])
            

    def newFeatures(self):
        
        if 'loss_year' in self.df.columns:
        # Calculate months until loss (positive = before, negative = after, None = no loss)
            self.df['months_until_loss'] = self.df.apply(
                lambda row: ((2000 + row['loss_year']) - row['year']) * 12 + (12 - row['month'])
                if row['loss_year'] > 0 else None,
                axis=1
            )

        if 'months_until_loss' in self.df.columns:
            # Use loc to conditionally set values of months_until_loss and loss year
            self.df['months_until_loss'] = self.df['months_until_loss'].astype(object)
            self.df['loss_year'] = self.df['loss_year'].astype(object)
            self.df.loc[(self.df['forest_loss'] == 0), 
                ['months_until_loss', 'loss_year']] = "No Loss"
            

        if 'ndvi' in self.df.columns:
            # compute delta to previous ndvi, and also a rolling mean over 3 months
            self.df['ndvi_roll_mean_3m'] = (
                self.df.groupby('id')['ndvi']
                .rolling(window=3, min_periods=1)
                .mean()
                .reset_index(0, drop=True))
            
        if 'precip_total_mm' in self.df.columns:
            # also computing an index for dryness; rainfall against temp
            self.df['dryness'] = self.df.apply(
            lambda row: row['precip_total_mm'] / row['lst_k'] if row['lst_k'] > 0 else 0,
            axis=1)
            self.df.drop('precip_lag1', axis=1, inplace=True)
            
        if 'sar_vv' and 'sar_vh' in self.df.columns:
            epsilon = 1e-6
            self.df['sar_ratio_db'] = 10 * np.log10(self.df['sar_vh'] / (self.df['sar_vv'] + epsilon))

        # new feature for spatial proximity to forest loss
        self.dist_from_loss()

        self.df.drop(['sar_vv', 'sar_vh'])

        return self


    def assert_types(self):
        # make date datetime
        self.df['date'] = pd.to_datetime(self.df['date'])

        def makeNumeric(df):
            exceptions = ['lat', 'long', 'date', 'months_until_loss', 'loss_year']
            # Convert all other columns to numeric
            for col in df.columns:
                if col not in exceptions:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                    return df
                
        self.df = makeNumeric(self.df)
        

    def temporal_interpolate(self, columns):
        
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
            group = self.df.groupby('id', group_keys=False)
            self.df = group.apply(
                lambda g: fill_with_yearly_mean(g, col), 
                include_groups=True).reset_index(drop=True)
        
        # FIXED: Add fallback linear interpolation for remaining (sort by date first)
        self.df = self.df.sort_values(['id', 'date'])
        for col in columns:
            self.df[col] = self.df.groupby('id')[col].transform(
                lambda x: x.interpolate(method='linear', limit_direction='both')
            )
        
        # FIXED: Final ffill/bfill for any edge/all-NaN cases
        for col in columns:
            self.df[col] = self.df.groupby('id')[col].transform(lambda x: x.ffill().bfill())

        self.df = self.df.dropna()

        print("DATA AFTER INTERPOLATION:::::::::::::")
        print(self.df.info(), "\n")
        print(self.df.describe(), "\n")
        print(self.df.isnull().sum(), "\n")

        return self
        

    def dist_from_loss(self):
            # Ensure data sorted by time
            self.df = self.df.sort_values(by=['year', 'month']).reset_index(drop=True)

            dist_values = []
            prev_loss_points = np.empty((0, 2))  # stores lat/long of previous losses

            for _, row in self.df.iterrows():
                if len(prev_loss_points) > 0:
                    # compute distance to *past* loss points only
                    dist = np.min(distance.cdist([[row['lat'], row['long']]], prev_loss_points))
                else:
                    dist = np.nan

                dist_values.append(dist)

                # if this record itself is a forest loss, add it to memory for future points
                if row['forest_loss'] == 1:
                    prev_loss_points = np.vstack([prev_loss_points, [row['lat'], row['long']]])

            self.df['dist_from_loss'] = dist_values
