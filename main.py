#!/usr/bin/env python3 

import os
from io import BytesIO

import requests
import urllib.request
import urllib.parse

import json

import xml.etree.ElementTree as xmlet
import lxml.etree as xmltree

import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from skimage import io
from PIL import Image as plimg
from PIL import ImageDraw

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

import cartopy.crs as ccrs
import cartopy
from cartopy.mpl.gridliner import LONGITUDE_FORMATTER, LATITUDE_FORMATTER
import folium
import mapbox_vector_tile

from owslib.wms import WebMapService
import geopandas as gpd
from shapely.geometry import box
import rasterio
from rasterio.mask import mask
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.plot import show
import fiona

from IPython.display import Image, display

def getCapabilities():
    # Construct WMTS capability URL.
    wmtsUrl = 'http://gibs.earthdata.nasa.gov/wmts/epsg4326/best/wmts.cgi?SERVICE=WMTS&REQUEST=GetCapabilities'

    # Request capabilities.
    response = requests.get(wmtsUrl)

    # Display capability XML.
    WmtsXml = xmltree.fromstring(response.content)

    # print(xmltree.tostring(WmtsXml, pretty_print = True, encoding = str))

    # Convert capability response to XML tree.
    WmtsTree = xmlet.fromstring(response.content)

    alllayer = []
    layerNumber = 0

    # Parse capability XML tree.
    for child in WmtsTree.iter():
        for layer in child.findall("./{http://www.opengis.net/wmts/1.0}Layer"): 
             if '{http://www.opengis.net/wmts/1.0}Layer' == layer.tag: 
                f=layer.find("{http://www.opengis.net/ows/1.1}Identifier")
                if f is not None:
                    alllayer.append(f.text)
                    layerNumber += 1

    # Print the first five and last five layers.
    # print('Number of layers: ', layerNumber)
    # for one in sorted(alllayer)[:5]:
    #     print(one)
    # print('...')
    # for one in sorted(alllayer)[-5:]:
    #     print(one)
    
    with open('wmts-capabilities.txt', 'w') as f:
        f.write(f"Number of Layers: {layerNumber}\n\n")
        for layer in alllayer:
            f.write(layer + "\n")
        print(f"Current Web Map Tile Service Capabilities exported to {f}")

def main():
    getCapabilities()

if __name__ == '__main__':
    main()




