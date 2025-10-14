import datetime
from datetime import datetime, timedelta
import time
import ee
import pandas as pd
from dateutil.relativedelta import relativedelta

def compose(start_date, end_date, region, 
            scale, elevation_bool, samples):
    # Dataset 1: MODIS NDVI (16-day, with quality filter)
    modis_ndvi = (ee.ImageCollection('MODIS/061/MOD13A1')
                  .filterDate(start_date, end_date)
                #   .filter(ee.Filter.lt('SummaryQA', 2))  # Good quality pixels
                  .select(['NDVI', 'EVI']))
    
    # Dataset 2: MODIS Land Surface Temperature (8-day)
    modis_lst = (ee.ImageCollection('MODIS/061/MOD11A2')
                 .filterDate(start_date, end_date)
                 .select(['LST_Day_1km']))
    
    # Dataset 3: Precipitation (daily, then aggregate)
    precip = (ee.ImageCollection('UCSB-CHG/CHIRPS/DAILY')
              .filterDate(start_date, end_date)
              .select(['precipitation']))
    
    # Dataset 4: Sentinel-1 SAR (for forest structure)
    s1 = (ee.ImageCollection('COPERNICUS/S1_GRD')
          .filterBounds(region)
          .filterDate(start_date, end_date)
          .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV'))
          .filter(ee.Filter.eq('orbitProperties_pass', 'DESCENDING'))  # Consistent orbit
          .select(['VV', 'VH']))
    
    # Dataset 5: Hansen Forest Change (static baseline)
    hansen = ee.Image('UMD/hansen/global_forest_change_2024_v1_12')
    forest_2000 = hansen.select('treecover2000')
    forest_loss = hansen.select('loss')
    forest_gain = hansen.select('gain')
    loss_year = hansen.select('lossyear')  # For temporal labeling
    
    # Optional: Elevation (static)
    if elevation_bool:
        elevation = ee.Image('USGS/SRTMGL1_003').select('elevation')
    
    # OKAY, let actually start sampling ey?
    # we'll sample static and dynamic layers differently
    # static layer sampling
    static_layers = ee.Image.cat([
    elevation.rename('elevation') if elevation_bool else None,
    forest_2000.rename('tree_cover_2000'),
    forest_loss.rename('forest_loss'),
    loss_year.rename('loss_year')
    ]) #.unmask()  # Handle nulls
    static_sample = static_layers.reduceRegions(
        collection=samples,
        reducer=ee.Reducer.mean(),
        scale=scale
    )
    static_data_points = static_sample.getInfo()['features']
    static_df = pd.DataFrame([f['properties'] for f in static_data_points])

    all_data = []
    current = datetime.strptime(start_date, '%Y-%m-%d')
    end_dt = datetime.strptime(end_date, '%Y-%m-%d')

    while current <= end_dt:
        month_start = current.strftime('%Y-%m-%d')
        
        # Get last day of current month
        next_month = current + relativedelta(months=1)
        last_day_of_month = next_month - timedelta(days=1)
        
        # Don't exceed end_date
        if last_day_of_month > end_dt:
            month_end_str = end_date
        else:
            month_end_str = last_day_of_month.strftime('%Y-%m-%d')
        
        print(f"Processing {month_start} to {month_end_str}...")
        
        
        # Monthly filter and composites (adapt your layers)
        modis_ndvi_month = modis_ndvi.filterDate(month_start, month_end_str)
        modis_lst_month = modis_lst.filterDate(month_start, month_end_str)
        precip_month = precip.filterDate(month_start, month_end_str)
        s1_month = s1.filterDate(month_start, month_end_str)

        # Right after filtering each collection, check if it's empty:
        modis_ndvi_month = modis_ndvi.filterDate(month_start, month_end_str)
        ndvi_count = modis_ndvi_month.size().getInfo()
        if ndvi_count == 0:
            print(f"  WARNING: No NDVI data for this period")

        temporal_layers = ee.Image.cat([
            modis_ndvi_month.select(['NDVI', 'EVI']).mean().rename(['ndvi_mean', 'evi_mean']),
            modis_lst_month.select('LST_Day_1km').mean().multiply(0.02).rename('lst_mean_k'),
            precip_month.select('precipitation').sum().rename('precip_total_mm'),
            s1_month.select(['VV','VH']).mean().rename(['sar_vv_mean', 'sar_vh_mean'])
        ])
        
        variability_layers = ee.Image.cat([
            modis_ndvi_month.select('NDVI').reduce(ee.Reducer.stdDev()).rename('ndvi_std'),
            modis_ndvi_month.select('NDVI').min().rename('ndvi_min'),
            modis_lst_month
                .select('LST_Day_1km').reduce(ee.Reducer.stdDev())
                .rename('lst_std'),
        ])
        
        # Combine all layers into one image
        monthly_layers = ee.Image.cat([ 
                                   temporal_layers, 
                                   variability_layers])  # Static is time-independent
        
        # Sample with just mean reducer (for spatial aggregation within buffers)
        sampling_data = monthly_layers.reduceRegions(
        collection=samples,
        reducer=ee.Reducer.mean(), # .combine(reducer2=ee.Reducer.stdDev(), sharedInputs=True),
        scale=scale
        )
        
        # Fetch and append with date info
        try:
            data_points = sampling_data.getInfo()['features']
            monthly_df = pd.DataFrame([f['properties'] for f in data_points])
            monthly_df['date'] = month_start
            monthly_df['month'] = current.month
            monthly_df['year'] = current.year
            # Merge with static
            monthly_df = monthly_df.merge(
                static_df[['id', 'elevation', 'tree_cover_2000', 'forest_loss', 'loss_year']],
                on='id',
                how='left'
            )
            all_data.append(monthly_df)
        except Exception as e:
            print(f"Error in month {month_start}: {e}")
            continue
        
        current = next_month
        time.sleep(1)  # Rate limit

    if not all_data:
        return None

    df = pd.concat(all_data, ignore_index=True)

    # DEBUG: See what we actually got
    print(f"\nColumns in final dataframe: {df.columns.tolist()}")
    print(f"Shape: {df.shape}")
    print(f"Sample row:\n{df.head(1)}")

    # Scale after (e.g., df['ndvi_mean'] *= 0.0001)
    # Scale after - proper conditional handling
    if 'ndvi_mean' in df.columns:
        df['ndvi_mean'] *= 0.0001
    if 'evi_mean' in df.columns:
        df['evi_mean'] *= 0.0001
    if 'ndvi_std' in df.columns:
        df['ndvi_std'] *= 0.0001
    if 'ndvi_min' in df.columns:
        df['ndvi_min'] *= 0.0001
    if 'lst_std' in df.columns:
        df['lst_std'] *= 0.02
    

    # Handle NaNs: Group by lat/long and forward-fill
    # df = df.sort_values(['lat', 'long', 'date'])
    # df = df.groupby(['lat', 'long']).apply(lambda g: g.ffill())
    print("\n")
    return df