import os
import requests
from datetime import datetime, timedelta

# Your layer_keys dict (from main.py; add if not there)
layer_keys = {
    'ndvi_monthly': 'MODIS_Terra_L3_NDVI_Monthly',
    'disturbance_annual': 'OPERA_L3_DIST-ANN-HLS_Color_Index',
    'forest_biomass': 'GEDI_ISS_L4B_Aboveground_Biomass_Density_Mean_201904-202303',
    # Add more as needed...
}

def download_wms_layer(layer_key, start_date, end_date, bbox, output_dir, interval_days=30):
    """
    Downloads WMS rasters for a layer over a time range.
    - layer_key: From layer_keys dict.
    - start_date/end_date: 'YYYY-MM-DD'
    - bbox: 'minx,miny,maxx,maxy' (e.g., Edo: '5.00,5.74,6.66,7.60')
    - output_dir: Folder to save TIFFs.
    - interval_days: 30 for monthly; adjust to 1 for daily (e.g., for alerts).
    """
    current_date = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    layer_name = layer_keys.get(layer_key)
    if not layer_name:
        print(f"Invalid layer key: {layer_key}")
        return
    
    os.makedirs(output_dir, exist_ok=True)
    print(f"Downloading {layer_key} from {start_date} to {end_date}...")
    
    while current_date <= end:
        time_str = current_date.strftime('%Y-%m-%d')
        url = (
            f"https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi?"
            f"version=1.3.0&service=WMS&request=GetMap&"
            f"format=image/tiff&STYLE=default&bbox={bbox}&CRS=EPSG:4326&"
            f"HEIGHT=1024&WIDTH=1024&TIME={time_str}&layers={layer_name}"
        )
        
        try:
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                file_path = os.path.join(output_dir, f"{layer_key}_{time_str}.tif")
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                print(f"Saved: {file_path}")
            else:
                print(f"Failed for {time_str}: Status {response.status_code}")
        except Exception as e:
            print(f"Error for {time_str}: {e}")
        
        current_date += timedelta(days=interval_days)

# Test usage: Run for one layer first
if __name__ == '__main__':
    edo_bbox = '5.00,5.74,6.66,7.60'  # Your provided coords
    test_dir = './data/edo_test'
    for layer in layer_keys:
        download_wms_layer(layer, '2020-01-01', '2024-01-01', edo_bbox, test_dir + f'{test_dir}/{layer}')
    # Then add: download_wms_layer('disturbance_annual', ...) etc. 