# -*- coding: utf-8 -*-
"""BurnedAreas_FIRECCI51.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1No27y-Gb3QJ2c6Hj85pFNju3JOIN86AO

## **BURNED AREA FIRECCI51 FOR ANDES FIRES PIPELINE**

* Import Libraries -> Check disponibilities of the libraries
 * Import Datasets -> Take dataset from GEE Catalog
 * Final Code:
  1. Preprocesing MCD64A1 -> Extract data from Data Catalog GEE.
  2. Download Burned Areas CSV -> Dowlondaing raw data format CSV
  3. Download Burned Areas SHP -> Dowlondaing raw data format SHP
  4. Data Filtering MCD64A1 -> Filtering and merge Burned Area CSV and SHP
  5. Merge Datasets -> Combine csv and shp files
  6. Calculate Area -> Calculate area of burned areas

#**Import Libraries**
"""

import ee
import geemap
from datetime import datetime
import pandas as pd
import numpy as np
from tqdm.notebook import tqdm
import geopandas as gpd

#Compte Earth Engine
ee.Authenticate()
ee.Initialize(project='ee-villa45ramos')

"""#**Import Datasets**"""

datasets= {'dem': ee.Image("USGS/SRTMGL1_003"),
           'WorldCoverESA':ee.ImageCollection('ESA/WorldCover/v100'),
           'countries':ee.FeatureCollection("FAO/GAUL_SIMPLIFIED_500m/2015/level0"),
           'andes':ee.Geometry.BBox( -84.0, -30.0, -62.0, 12.0).buffer(1000),
           'FireCCI51':ee.ImageCollection("ESA/CCI/FireCCI/5_1"),
           'startDate' : '2012-01-01',#2001-01-01 and 2012-01-01
           'endDate' : '2024-01-01',#2011-12-30 and 2024-01-01
           'dir_csv':'/content/drive/MyDrive/PFE_CIRAD_AMAP/3_FIRECCI/Inter_data_FireCCI/FireCCI_BA_Country_2000-01-01_2012-01-01.csv',#change csv (2 parts)
           'dir_shp':'/content/drive/MyDrive/PFE_CIRAD_AMAP/3_FIRECCI/Inter_data_FireCCI/FireCCI_BA_Country_2000-01-01_2012-01-01.shp',#change shp (2 parts)
           'dir1_csv':'/content/drive/MyDrive/PFE_CIRAD_AMAP/3_FIRECCI/Inter_data_FireCCI/FireCCI_BA_Country_2000-01-01_2012-01-01.csv',
           'dir1_shp':'/content/drive/MyDrive/PFE_CIRAD_AMAP/3_FIRECCI/Inter_data_FireCCI/FireCCI_BA_Country_2000-01-01_2012-01-01.shp',
           'dir2_csv':'/content/drive/MyDrive/PFE_CIRAD_AMAP/3_FIRECCI/Inter_data_FireCCI/FireCCI_BA_Country_2012-01-01_2024-01-01.csv',
           'dir2_shp':'/content/drive/MyDrive/PFE_CIRAD_AMAP/3_FIRECCI/Inter_data_FireCCI/FireCCI_BA_Country_2012-01-01_2024-01-01.shp'}

"""# **Final Code**

## *1. Preprocesing FIRECC51*
"""

# -*- coding: utf-8 -*-
"""
Created on 22/10/2024 19:15:46
Version 2.0.0
@author: jvilla
"""
def BurnedAreasFireCCI(roi,dem,wc,firecci51,pays,startDate,endDate):
  """
  This function extract Burned Areas from FIRECCI51 projet

  Parameters:
  ----------------------
  roi: ee.Geometry
    Region of interest (geometry).
  dem: ee.Image
    DEM Elevation data.
  wc: ee.ImageCollection
    WorldCover image collection.
  firecci51: ee.ImageCollection
    FireCCI51 image collection.
  pays: ee.FeatureCollection
    List of countries.
  starDate: str
    Start date for filtering.
  endDate: str
    End date for filtering.

  Returns:
  ----------------------
  Extract_BA: ee.FeatureCollection
    Collection of burned areas.
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
      FIAndes = firecci51.filterDate(startDate,endDate)
      burnedArea = FIAndes.filterBounds(elev_moscaic.geometry()).map(clipStudyArea).map(cpPro)
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
    burnedArea = BurnedArea(firecci51, roi, elev_mosaic)

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
      projec = ee.Image(burnedArea.select(0).first()).projection().nominalScale()
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
      return sum_flatten
    Extract_BA=Extract_Burned_Areas(GetProjection(sum_ba))
    return Extract_BA

  except Exception as e:
    print(f"An error occurred: {e}")

FireCCI_BA=BurnedAreasFireCCI(datasets['andes'],datasets['dem'],datasets['WorldCoverESA'],datasets['FireCCI51'],datasets['countries'],datasets['startDate'],datasets['endDate'])
print("Processus terminée")

"""## *2.  Download Burned Areas CSV*"""

task = ee.batch.Export.table.toDrive(
    collection=FireCCI_BA,
    description=f'FireCCI_BA_Country_{startDate}_{endDate}',
    folder='Inter_data_FireCCI',
    fileFormat='CSV')
task.start()
print(f"Execution entre: {startDate}_{endDate}")

"""## *3. Download Burned Areas SHP*"""

startDate = datasets['startDate']
endDate = datasets['endDate']
task = ee.batch.Export.table.toDrive(
    collection=FireCCI_BA,
    description=f'FireCCI_BA_Country_{startDate}_{endDate}',
    folder='Inter_data_FireCCI',
    fileFormat='SHP')
task.start()
print(f"Execution entre: {startDate}_{endDate}")

"""## *4. Data Filtering MCD64A1*"""

# -*- coding: utf-8 -*-
"""
Modified on 22/10/2024 19:25:24
Version 2.0.0
@author: jvilla
"""
def filt_concat(dir_csv,dir_shp):
  """
  This function filter collection for country, elevation, climate zone and soil type

  Parameters:
  ---------------------
  dir_csv: str
    Path to the CSV file to filter.
  dir_shp: str
    Path to the SHP file to filter.

  Returns:
  ---------------------
  gdft_concat: gpd.GeoDataFrame
    Filtered and concatenated GeoDataFrame.
  """

  try:
    dtf=pd.read_csv(dir_csv)
    gdft=gpd.read_file(dir_shp)
    gdft_concat = gpd.GeoDataFrame(pd.concat([dtf, gdft],axis=1),crs=gdft.crs)
    gdft_concat=gdft_concat.iloc[:,[0,1,2,3,4,5,6,7,15]]
    gdft_concat=gdft_concat.dropna(subset=['country'])
    gdft_concat=gdft_concat[gdft_concat['elevation'] >= 2000]
    gdft_concat=gdft_concat.to_crs(3857)
    conditionlist = [
      (gdft_concat["country"] == 195),#Peru
      (gdft_concat["country"] == 51),#Chile
      (gdft_concat["country"] == 12),#Argentina
      (gdft_concat["country"] == 33),#Bolivia
      (gdft_concat["country"] == 73),#Ecuador
      (gdft_concat["country"] == 57),#Colombia
      (gdft_concat["country"] == 263)#Venezuela
      ]
    choicelist = ["Peru","Chile","Argentina","Bolivia","Ecuador","Colombia","Venezuela"]
    gdft_concat["Pays"] = np.select(conditionlist, choicelist, default="Not Specified")
    gdft_concat["latitude"]=gdft_concat.centroid.y
    conditionlist = [
      (gdft_concat["latitude"] >= -557305.2572745768),#-557305.2572745768 equivalent a -5 en pseduMercator
      (gdft_concat["latitude"] >= -893463.751012646) & (gdft_concat["latitude"] < -557305.2572745768),#-893463.751012646 equivalent a -8 en pseduMercator
      (gdft_concat["latitude"] <= -893463.751012646)]
    choicelist = ["Zone_Equatorial", "Transition_Zone", "South_Zone"]
    gdft_concat["Zone_Clima"] = np.select(conditionlist, choicelist, default="Not Specified")
    gdft_concat=gdft_concat[gdft_concat['Map'] <= 40]
    gdft_concat['Map']=gdft_concat['Map'].replace([10, 20, 30, 40], ["Tree cover", "Shrubland", "Grassland", "Cropland"])
    gdft_concat["year"]=""
    gdft_concat["month"]=""
    for i in tqdm(range(0,gdft_concat.shape[0])):
      gdft_concat["year"].iloc[i]=gdft_concat['system:index'].iloc[i][0:4]
      gdft_concat["month"].iloc[i]=gdft_concat['system:index'].iloc[i][5:7]
    gdft_concat=gdft_concat[gdft_concat['ConfidenceLevel'] >= 80]
    gdft_concat=gdft_concat.iloc[:,[2,3,6,7,9,11,12,13,8]]#column pays???
    gdft_concat.columns=['lc_100m','wc_10m','Elevation(m)','BurnDate(doy)','Pays','Zone_Climatique','Annee','Mois','geometry']
    return gdft_concat

  except Exception as e:
    print(f"An error occurred: {e}")

#FireCCI PARTIE 1 -> 2000-2012
FireCCI_BA_part1=filt_concat(datasets['dir1_csv'],datasets['dir1_shp']).to_file('/content/drive/MyDrive/PFE_CIRAD_AMAP/3_FIRECCI/Outputs_FireCCI/FireCCI_BA_join_2000_2012.shp')

#FireCCI PARTIE 2 -> 2012-2024
FireCCI_BA_part2=filt_concat(datasets['dir2_csv'],datasets['dir2_shp']).to_file('/content/drive/MyDrive/PFE_CIRAD_AMAP/3_FIRECCI/Outputs_FireCCI/FireCCI_BA_join_2012_2024.shp')

print("Processus terminée Filtration Donnees CSV et SHP")

"""## *5. Merge Datasets*"""

FireCCI_part1=gpd.read_file('/content/drive/MyDrive/PFE_CIRAD_AMAP/3_FIRECCI/Outputs_FireCCI/FireCCI_BA_join_2000_2012.shp')
FireCCI_part2=gpd.read_file('/content/drive/MyDrive/PFE_CIRAD_AMAP/3_FIRECCI/Outputs_FireCCI/FireCCI_BA_join_2012_2024.shp')
gdft_concat = gpd.GeoDataFrame(pd.concat([FireCCI_part1,FireCCI_part2],axis=0),crs=FireCCI_part1.crs).to_file('/content/drive/MyDrive/PFE_CIRAD_AMAP/3_FIRECCI/Outputs_FireCCI/FireCCI_BA_join_all.shp')

"""## *6. Calculate Area*"""

gdf = gpd.read_file('/content/drive/MyDrive/PFE_CIRAD_AMAP/3_FIRECCI/Outputs_FireCCI/FireCCI_BA_join_all.shp')
gdf["Area(hec)"]=(gdf.area)/10000
gdtf=gdf.iloc[:,[0,1,2,3,4,5,6,7,9,8]]
gdtf.to_csv('/content/drive/MyDrive/PFE_CIRAD_AMAP/3_FIRECCI/Outputs_FireCCI/FireCCI_BA_join_all.csv',index=False)