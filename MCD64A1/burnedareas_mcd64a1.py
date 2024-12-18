# -*- coding: utf-8 -*-
"""BurnedAreas_MCD64A1.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1Z-TETgobdFBiZ-IRT8KtjPA4VzF1Evvv

## **BURNED AREA MCD64A1 FOR ANDES FIRES PIPELINE**

* Import Libraries -> Check disponibilities of the libraries
 * Import Datasets -> Take dataset from GEE Catalog
 * Final Code:
  1. Preprocesing MCD64A1 -> Extract data from Data Catalog GEE.
  2. Download Burned Areas CSV -> Dowlondaing raw data format CSV
  3. Download Burned Areas SHP -> Dowlondaing raw data format SHP
  4. Data Filtering MCD64A1 -> Filtering and merge Burned Area CSV and SHP

#**Import Libraries**
"""

import ee
import geemap
from datetime import datetime
import pandas as pd
import numpy as np
import geopandas as gpd
from tqdm.notebook import tqdm

#Compte Earth Engine
ee.Authenticate()
ee.Initialize(project='ee-villa45ramos')

"""#**Import Datasets**"""

datasets= {'dem': ee.Image("USGS/SRTMGL1_003"),
           'WorldCoverESA':ee.ImageCollection('ESA/WorldCover/v100'),
           'MCD64A1':ee.ImageCollection("MODIS/061/MCD64A1"),
           'countries':ee.FeatureCollection("FAO/GAUL_SIMPLIFIED_500m/2015/level0"),
           'andes':ee.Geometry.BBox(-84.0, -30.0, -62.0, 12.0).buffer(1000),
           'dir_csv':'/content/drive/MyDrive/PFE_CIRAD_AMAP/2_MCD64A1/Inter_data_BurnedArea/MODIS_BurnedAreas_country.csv',
		       'dir_shp':'/content/drive/MyDrive/PFE_CIRAD_AMAP/2_MCD64A1/Inter_data_BurnedArea/MODIS_BurnedAreas_country.shp'}

"""#**Final Code**

## *1. Preprocesing MCD64A1*
"""

# -*- coding: utf-8 -*-
"""
Modified on 28/09/2024 15:41:06
Version 3.0.0
@author: jvilla
"""
def BurnedAreaMODIS(roi,dem,wc,mcd64a1,pays):
  """
  This function extracts Burned Area from MODIS MCD64A1.

  Parameters:
  -------------
  roi: ee.Geometry
    Region of interest (geometry).
  dem: ee.Image
    DEM Elevation data.
  wc: ee.ImageCollection
    WorldCover image collection.
  mcd64a1: ee.ImageCollection
    MODIS MCD64A1 image collection.
  pays: ee.FeatureCollection
    List of countries.

  Returns:
  -------------
  Extract_BA: ee.FeatureCollection
    Collection of burned area features.
  """
  try:
    def elevation(dem,roi):
      dem2 = dem.clip(roi)
      elev = dem2.gte(2000)
      elev_moscaic = dem2.updateMask(elev)
      return elev_moscaic

    def worldcover(roi,wc):
      def clipStudyArea(img):
        return img.clip(roi)
      return wc.filterBounds(roi).map(clipStudyArea).mosaic()

    elev_mosaic = elevation(dem, roi)

    def BurnedArea(mcd64a1,roi,elev_moscaic):
      def clipStudyArea(img):
        return img.clip(roi)
      def cpPro(img):
          return img.copyProperties(img, ["system:time_start"])
      burnedArea = mcd64a1.filterBounds(elev_moscaic.geometry()).map(clipStudyArea).map(cpPro)
      return burnedArea

    def country(pays):
      countries = ee.List([195,51,12,33,73,57,263]); #Peru, Chile, Argentina,BOlivia, Ecuador, Colombia, Venezuela
      countriesshp = pays.filter(ee.Filter.inList('ADM0_CODE',countries))
      filterc = ee.Filter.inList('ADM0_CODE',countries)
      countriesshp = pays.filter(filterc)
      def remove_non_polygons(geometry):
        return ee.Algorithms.If(ee.Algorithms.IsEqual(ee.Geometry(geometry).type(),ee.String('Polygon')),ee.Feature(ee.Geometry(geometry)),None)
      def clean_polygon_feature(feature):
        geometries = feature.geometry().geometries()
        geometries_cleaned = ee.FeatureCollection(geometries.map(remove_non_polygons)).union().first()
        return ee.Feature(feature).setGeometry(geometries_cleaned.geometry())
      return countriesshp.map(clean_polygon_feature)

    countries_shp = country(pays)

    def ToImage(countries_shp):
      toImage=countries_shp.reduceToImage(['ADM0_CODE'], 'first')#Convert to Image (needs numering or int input)
      return toImage

    wc_mosaic = worldcover(roi, wc)
    toImage_result = ToImage(countries_shp)
    burnedArea = BurnedArea(mcd64a1, roi, elev_mosaic)

    def summary(wc_mosaic,dem,roi,toImage_result,burnedArea):
      def selec_prop(image):
        wc_prop = wc_mosaic.select('Map')
        elev_prop = dem.clip(roi).select('elevation')
        country = toImage_result.select('first').rename('country')
        return image.addBands(wc_prop).addBands(elev_prop).addBands(country)
      sum_ba=burnedArea.map(selec_prop)
      return sum_ba

    sum_ba=summary(wc_mosaic,dem,roi,toImage_result,burnedArea)

    def GetProjection(burnedArea):
      projec = ee.Image(burnedArea.first()).projection().nominalScale()
      return projec

    projec_ba=GetProjection(burnedArea)

    def Extract_Burned_Areas(projec):
      def trf_to_fc(image):
        image = image.reduceToVectors(
                  reducer=ee.Reducer.first(),
                  scale=projec_ba,
                  maxPixels=1e10)
        return ee.FeatureCollection(image)

      sum_flatten = sum_ba.map(trf_to_fc).flatten()
      def shapeCount(feat):
        feat = ee.Feature(feat)
        name = feat.get('ADM0_NAME')
        def namecount(sum_flatten):
          return ee.Feature(sum_flatten).set('Country', name)
        return sum_flatten.filterBounds(feat.geometry()).map(namecount)
      extract_BA = countries_shp.map(shapeCount).flatten()
      return extract_BA

    Extract_BA=Extract_Burned_Areas(GetProjection(sum_ba))
    return Extract_BA

  except Exception as e:
    print(f"An error occurred: {e}")

BurnedArea_Proces=BurnedAreaMODIS(datasets['andes'],datasets['dem'],datasets['WorldCoverESA'],datasets['MCD64A1'],datasets['countries'])
print("Processus FireActivity terminée")

"""## *2.  Download Burned Areas CSV*"""

task = ee.batch.Export.table.toDrive(
    collection=BurnedArea_Proces,
    description='MODIS_BurnedAreas_country',
    folder='Inter_data_BurnedArea',
    fileFormat='CSV')

task.start()

"""## *3. Download Burned Areas SHP*"""

task = ee.batch.Export.table.toDrive(
    collection=BurnedArea_Proces,
    description='MODIS_BurnedAreas_country',
    folder='Inter_data_BurnedArea',
    fileFormat='SHP')

task.start()

"""## *4. Data Filtering MCD64A1*"""

# -*- coding: utf-8 -*-
"""
Modified on 28/09/2024 16:04:13
Version 3.0.0
@author: jvilla
"""
"""
This function filter and merge Burned Area CSV and SHP

Parameters:
-----------
dir_csv: str
	Path to the CSV file to filter.
dir_shp: str
	Path to the SHP file to filter.

Returns:
-----------
gdtf: geopandas.GeoDataFrame
	Filtered and merged GeoDataFrame.

"""
def filt_concat(dir_csv,dir_shp):
	try:
		dtf=pd.read_csv(dir_csv)
		gdft=gpd.read_file(dir_shp)
		gdft_concat = gpd.GeoDataFrame(pd.concat([dtf, gdft],axis=1),crs=gdft.crs)
		gdtf=gdft_concat.iloc[:,[0,1,2,3,4,8,9,20]]
		gdtf=gdtf[gdtf['elevation'] >= 2000]
		gdtf=gdtf.to_crs(3857)
		gdtf["latitude"]=gdtf.centroid.y
		conditionlist = [
    (gdtf["latitude"] >= -557305.2572745768),
    (gdtf["latitude"] >= -893463.751012646) & (gdtf["latitude"] < -557305.2572745768),
    (gdtf["latitude"] <= -893463.751012646)]
		choicelist = ["Zone_Equatorial", "Transition_Zone", "South_Zone"]
		gdtf["Zone_Clima"] = np.select(conditionlist, choicelist, default="Not Specified")
		gdtf=gdtf[gdtf['Map'] <= 40]
		gdtf["year"]=""
		gdtf["month"]=""
		for i in tqdm(range(0,gdtf.shape[0])):
			gdtf["year"].iloc[i]=gdtf['system:index'].iloc[i][21:25]
			gdtf["month"].iloc[i]=gdtf['system:index'].iloc[i][26:28]
		gdtf=gdtf.iloc[:,[1,2,3,4,5,6,9,10,11,7]]
		gdtf.columns=['Pays','FirstDate','LastDay','WordlCover','Elevation(m)','BurnDate(doy)','Zone_Climatique','Annee','Month','geometry']
		gdtf['WordlCover']=gdtf['WordlCover'].replace([10, 20, 30, 40], ["Tree cover", "Shrubland", "Grassland", "Cropland"])
		return gdtf
	except Exception as e:
		print(f"An error occurred: {e}")

MCD64A1_BA=filt_concat(datasets['dir_csv'],datasets['dir_shp']).to_file('/content/drive/MyDrive/PFE_CIRAD_AMAP/2_MCD64A1/Outputs_BurnedArea/MODIS64A1_BA_join.shp')
print("Processus terminée Filtration Donnees CSV et SHP")