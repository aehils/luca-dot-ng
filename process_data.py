import sys
import pandas as pd
import numpy as np

def extract_features(df):

    if 'forest_loss' in df.columns:
        df['forest_loss'] = (df['forest_loss'] > 0).astype(int)
        if 'loss_year' in df.columns:
            df['forest_loss'] = (df['loss_year'] > 0).astype(int)
    
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
               ['months_until_loss', 'loss_year']] = ["No Loss", "None"]
    
    if 'sar_vv_mean' in df.columns and 'sar_vh_mean' in df.columns:
        df = df.dropna(subset=['sar_vv_mean', 'sar_vh_mean'])

    # filter rows where there was no tree cover
    df = df[df['tree_cover_2000'] != 0]

    return df

def makeNumeric(df):
    exceptions = ['lat', 'long', 'date', 'months_until_loss', "loss_year"]

    # Convert all other columns to numeric
    for col in df.columns:
        if col not in exceptions:
            df[col] = pd.to_numeric(df[col], errors='coerce')


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
        df = df.groupby('id').apply(lambda g: fill_with_yearly_mean(g, col)).reset_index(drop=True)

    # Apply to each id group for specific columns
    for col in columns:
        df = df.groupby('id').apply(lambda g: fill_with_yearly_mean(g, col)).reset_index(drop=True)
    
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
    return df