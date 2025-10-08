import rasterio
import matplotlib.pyplot as plt
import os

def validate_tiff(file_path):
    with rasterio.open(file_path) as src:
        print(f"CRS: {src.crs}, Bounds: {src.bounds}, Shape: {src.shape}")
        data = src.read(1)  # Read first band
        plt.imshow(data, cmap='viridis')  # NDVI: green-yellow-red scale
        plt.colorbar(label='NDVI Value')
        plt.title(f"Sample: {os.path.basename(file_path)}")
        plt.show()

# Usage after download
validate_tiff('./data/edo_test/ndvi_monthly/ndvi_monthly_2022-12-16.tif')