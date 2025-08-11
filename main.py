import requests
import json
from urllib.parse import urlencode

import numpy as py
import pandas as pd

import matplotlib.pyplot as plot
import matplotlib.colors as colours

from datetime import datetime, timedelta

try:
    import rasterio
    from rasterio.plot import show
    print("Satellite image rasterisation is available.")
except:
    print("rasterio unavailable: Satellite images cannot be processed")




