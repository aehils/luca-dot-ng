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

# WMS !
wmsUrl = 'https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi?SERVICE=WMS&REQUEST=GetCapabilities'
# Construct capability URL. ^
response = requests.get(wmsUrl) # Request WMS capabilities.
WmsXml = xmltree.fromstring(response.content)# Display capabilities XML in original format. Tag and content in one line.
# print(xmltree.tostring(WmsXml, pretty_print = True, encoding = str))
WmsTree = xmlet.fromstring(response.content) # Coverts response to XML tree.

layer_keys = {
    # Primary Forest/Vegetation Indicators
    'forest_biomass': 'GEDI_ISS_L4B_Aboveground_Biomass_Density_Mean_201904-202303',
    'canopy_height': 'GEDI_ISS_L3_Canopy_Height_Mean_RH100_201904-202303',
    'land_cover': 'MODIS_Combined_L3_IGBP_Land_Cover_Type_Annual',
    'ndvi_8day': 'MODIS_Terra_NDVI_8Day',
    'ndvi_16day': 'MODIS_Terra_L3_NDVI_16Day',
    'ndvi_monthly': 'MODIS_Terra_L3_NDVI_Monthly',
    'evi_8day': 'MODIS_Terra_EVI_8Day',
    'evi_16day': 'MODIS_Terra_L3_EVI_16Day',
    'evi_monthly': 'MODIS_Terra_L3_EVI_Monthly',
    'lai': 'MODIS_Combined_L4_LAI_8Day',
    'fpar': 'MODIS_Combined_L4_FPAR_8Day',
    
    # Deforestation/Disturbance Detection
    'disturbance_alerts': 'OPERA_L3_DIST-ALERT-HLS_Color_Index',
    'disturbance_annual': 'OPERA_L3_DIST-ANN-HLS_Color_Index',
    'thermal_anomalies': 'MODIS_Combined_Thermal_Anomalies_All',
    'fire_viirs': 'VIIRS_SNPP_Thermal_Anomalies_375m_All',
    'fire_day': 'MODIS_Combined_Thermal_Anomalies_Day',
    'fire_night': 'MODIS_Combined_Thermal_Anomalies_Night',
    
    # Land Use/Human Impact
    'croplands': 'Agricultural_Lands_Croplands_2000',
    'pastures': 'Agricultural_Lands_Pastures_2000',
    'built_up': 'Landsat_Human_Built-up_And_Settlement_Extent',
    'settlements': 'GRUMP_Settlements',
    'urban_extents': 'GRUMP_Urban_Extents_Grid_1995',
    'population_density': 'GPW_Population_Density_2020',
    
    # Climate/Environmental Context
    'temperature': 'MERRA2_2m_Air_Temperature_Monthly',
    'precipitation': 'IMERG_Precipitation_Rate',
    'water_vapor': 'MERRA2_Total_Precipitable_Water_Vapor_Monthly',
    'soil_moisture': 'SMAP_L4_Analyzed_Surface_Soil_Moisture',
    
    # High-Resolution Imagery
    'true_color_landsat': 'Landsat_WELD_CorrectedReflectance_TrueColor_Global_Monthly',
    'true_color_modis': 'MODIS_Terra_CorrectedReflectance_TrueColor',
    'surface_reflectance': 'MODIS_Terra_SurfaceReflectance_Bands121',
    
    # Forest Health/Productivity
    'gpp': 'MODIS_Terra_L4_Gross_Primary_Productivity_8Day',
    'net_photosynthesis': 'MODIS_Terra_L4_Net_Photosynthesis_8Day',
    
    # Additional Useful Layers
    'mangroves': 'Mangrove_Forest_Distribution_2000',
    'surface_water': 'OPERA_L3_Dynamic_Surface_Water_Extent-HLS',
    'land_surface_temp': 'MODIS_Terra_Land_Surface_Temp_Day',

    'cr157': 'Landsat_WELD_CorrectedReflectance_Bands157_Global_Annual'
}

def getCapabilitiesWMS():

    alllayer = []
    layerNumber = 0

    # Parse XML.
    for child in WmsTree.iter():
        for layer in child.findall("./{http://www.opengis.net/wms}Capability/{http://www.opengis.net/wms}Layer//*/"): 
            if layer.tag == '{http://www.opengis.net/wms}Layer': 
                f = layer.find("{http://www.opengis.net/wms}Name")
                if f is not None:
                    alllayer.append(f.text)
                    
                    layerNumber += 1

    with open('wms-capabilities.txt', 'w') as file:
        file.write(f"Number of Layers: {layerNumber} \n\n")
        for layer in alllayer:
            file.write(layer + "\n")
        print(f"Web Map Service capabilities exported to {file}")

def layerAttributesWMS(key):
    # Define layername to use.
    layerName = key 

    # Get general information of WMS.
    for child in WmsTree.iter():
        if child.tag == '{http://www.opengis.net/wms}WMS_Capabilities': 
            print('Version: ' +child.get('version'))
        
        if child.tag == '{http://www.opengis.net/wms}Service': 
            print('Service: ' +child.find("{http://www.opengis.net/wms}Name").text)
            
        if child.tag == '{http://www.opengis.net/wms}Request': 
            print('Request: ')
            for e in child:
                print('\t ' + e.tag.partition('}')[2])
                                
            all = child.findall(".//{http://www.opengis.net/wms}Format")
            if all is not None:
                print("Format: ")
                for g in all:
                    print("\t " + g.text)     
                    
            for e in child.iter():
                if e.tag == "{http://www.opengis.net/wms}OnlineResource":
                    print('URL: ' + e.get('{http://www.w3.org/1999/xlink}href'))
                    break

    # Get layer attributes.
    for child in WmsTree.iter():
        for layer in child.findall("./{http://www.opengis.net/wms}Capability/{http://www.opengis.net/wms}Layer//*/"): 
            if layer.tag == '{http://www.opengis.net/wms}Layer': 
                f = layer.find("{http://www.opengis.net/wms}Name")
                if f is not None:
                    if f.text == layerName:
                        # Layer name.
                        print('Layer: ' + f.text)
                        
                        # All elements and attributes:
                        # CRS
                        e = layer.find("{http://www.opengis.net/wms}CRS")
                        if e is not None:
                            print('\t CRS: ' + e.text)
                        
                        # BoundingBox.
                        e = layer.find("{http://www.opengis.net/wms}EX_GeographicBoundingBox")
                        if e is not None:
                            print('\t LonMin: ' + e.find("{http://www.opengis.net/wms}westBoundLongitude").text)
                            print('\t LonMax: ' + e.find("{http://www.opengis.net/wms}eastBoundLongitude").text)
                            print('\t LatMin: ' + e.find("{http://www.opengis.net/wms}southBoundLatitude").text)
                            print('\t LatMax: ' + e.find("{http://www.opengis.net/wms}northBoundLatitude").text)
                        
                        # Time extent.
                        e = layer.find("{http://www.opengis.net/wms}Dimension")
                        if e is not None:
                            print('\t TimeExtent: ' + e.text)
                            
                        # Style.
                        e = layer.find("{http://www.opengis.net/wms}Style")
                        if e is not None:
                            f = e.find("{http://www.opengis.net/wms}Name")
                            if f is not None:
                                print('\t Style: ' + f.text)

    print('')                         


def main():
    getCapabilitiesWMS()
    layerAttributesWMS(layer_keys['forest_biomass'])

if __name__ == '__main__':
    main()




