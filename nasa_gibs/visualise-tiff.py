import rasterio
import matplotlib.pyplot as plt
import numpy as np

with rasterio.open('./data/edo_test/forest_biomass/forest_biomass_2022-10-17.tif') as src:
    data = src.read(1)  # Read first band
    print(f"Data range: {data.min()} to {data.max()}")
    print(f"Data type: {data.dtype}")
    print(f"Shape: {data.shape}")
    
    plt.imshow(data, cmap='gray')
    plt.colorbar()
    plt.show()