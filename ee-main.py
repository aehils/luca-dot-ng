#!/usr/bin/env python3

import sys
import ee
import pandas as pd
from datetime import datetime, timedelta

def startEarthEngine():

    ee.Authenticate()
    try:
        ee.Initialize(project='sage-courier-474421-m9')
    except Exception as e:
        print(f"Could not start Earth Engine: {e}")
        # sys.exit(1)
    else:
        print("✓ Earth Engine initialized")

if __name__ == '__main__':
    startEarthEngine()
    print(ee.String('Hello from the Earth Engine servers!').getInfo())

    # Load a Landsat image.
    img = ee.Image('LANDSAT/LT05/C02/T1_L2/LT05_034033_20000913')
    # Print image object WITHOUT call to getInfo(); prints serialized request instructions.
    print(img.getInfo())