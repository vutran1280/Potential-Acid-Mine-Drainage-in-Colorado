# -*- coding: utf-8 -*-
"""
Created on Tue Apr 12 12:54:51 2022

@author: tuanv
"""
import arcpy
from arcpy import env
import os
import sys
import pandas as pd


path=r'C:\Users\tuanv\Desktop\Energy' #sets the path to my Lab4 folder
env.workspace = path+'\data' #sets the workspace to the data folder
outpath = path + '\output' #sets where things are saved to the ouput folder
env.overwriteOutput = 1
sys.path[0]
arcpy.CheckOutExtension('SPATIAL')





print 'PART 1'
#Part 1 Idenfity toxic drainage 
    
def AppendPoint(shapefile,ListX,ListY):
    '''
    shapefile: input shapefile
    ListX: List of X coordinates
    ListY: List of Y coordinates
    '''
    if arcpy.Exists(shapefile):
        arcpy.management.Delete(shapefile)
    arcpy.CreateFeatureclass_management(env.workspace,shapefile,'POINT')
    point = arcpy.Point()
    array = arcpy.Array()
    count = 0
    for i in ListX:
        point.X = i
        point.Y = ListY[count]
        array.append(point)
        count = count +1
    with arcpy.da.InsertCursor(shapefile,['SHAPE@']) as cursor:
        for p in array:
            cursor.insertRow([p])
    print 'Successfully added points to',shapefile, 'feature class'
  

        
def DefineProjection(ProjectionSource,inputShapefile,outputShapefile):
    '''
    ProjectionSource: The source you want to get the projection from
    inputShapefile: The shapefile which projection need to be defined
    outputShapefile: The result shapefile after reprojection. 
    '''
    crs = arcpy.Describe(ProjectionSource).spatialReference 
    arcpy.management.DefineProjection(inputShapefile,crs)
    arcpy.management.Project(inputShapefile,outputShapefile,crs)


#Declaring Variables
mines = "Hole_Openings.shp"
water = 'water_testing.shp'
dump = 'dump_sites.shp'
watershed = 'wbdhu10.shp'
    
finalPointsMines = 'finalPointsMines.shp'
finalPointsDump = 'finalPointsDump.shp'
finalPointsWater = 'finalPointsWater.shp'

Xcoord = []
Ycoord = []
Xcoord2 = []
Ycoord2 = [] 
Xcoord3 = []
Ycoord3 = []


#Running Query using search cursor based on criteria
with arcpy.da.SearchCursor(mines,['SHAPE@','DRAINAGE','ENV_RATING']) as cursor:
    for row in cursor:
        if (row[1] == 'water draining' and (row[2] == 'extreme' or row[2] == 'significant' or row[2] == 'potentially significant')):
            Xcoord.append(row[0].getPart(0).X)
            Ycoord.append(row[0].getPart(0).Y)
 
with arcpy.da.SearchCursor(dump,['SHAPE@','DRAINAGE','ENV_RATING','SLOPE_ANG','CEMENT','STORM_EROD']) as cursor:
    for row in cursor:
        if ((row[1] == 'water draining across surface' or row[1] == 'water seeping from side of feature' or row[1] =='water draining across surface, water seeping from side of feature' ) and (row[2] == 'extreme' or row[2] == 'significant' or row[2] == 'potentially significant' or row[2] == 'slight') and (row[3]>10) and (row[4] == 'uncemented') and (row[5]=='in contact with normal stream')):
            Xcoord2.append(row[0].getPart(0).X)
            Ycoord2.append(row[0].getPart(0).Y)        

with arcpy.da.SearchCursor(water,['SHAPE@','PH','CONDUCT']) as cursor:
    for row in cursor:
        if (row[1] < 5) and (row[2] > 2500) :
            Xcoord3.append(row[0].getPart(0).X)
            Ycoord3.append(row[0].getPart(0).Y)
            
AppendPoint(finalPointsMines,Xcoord,Ycoord)
AppendPoint(finalPointsDump,Xcoord2,Ycoord2)
AppendPoint(finalPointsWater,Xcoord3,Ycoord3) 

#Define Projection 
DefineProjection(mines,finalPointsMines,'finalPointsMinesProjected.shp')
DefineProjection(dump,finalPointsDump,'finalPointsDumpProjected.shp')
DefineProjection(water,finalPointsWater,'finalPointsWaterProjected.shp')

#Spatial Join watershed with points to count number of points inside each watershed
arcpy.analysis.SpatialJoin(watershed,'finalPointsMinesProjected.shp', 'minesJoined.shp')
arcpy.analysis.SpatialJoin('minesJoined.shp','finalPointsDumpProjected.shp', 'dumpJoined.shp')
arcpy.analysis.SpatialJoin('dumpJoined.shp','finalPointsWaterProjected.shp',os.path.join(outpath,'Points_Polygons_Joined.shp'))

#Create new list of SiteScore = Sum of points of three point feature class within each watershed polygon
SiteScore = []                    
with arcpy.da.SearchCursor(os.path.join(outpath,'Points_Polygons_Joined.shp'),['SHAPE@','Join_Count','Join_Cou_1','Join_Cou_2']) as cursor:
    for row in cursor:
        SiteScore.append(row[1]+(row[2])+(row[3]*2)) #The total score for each watershed polygon is the sum of the number of 
        #points of abandoned mines, dumping sites, and water testing sites (x2 for water testing sites because it actually 
        #show the parameter of water)
        
#Add SiteScore field                          
arcpy.management.AddField(os.path.join(outpath,'Points_Polygons_Joined.shp'), 'SiteScore','FLOAT')
print 'Site_Score field has been created for',os.path.join(outpath,'Points_Polygons_Joined.shp')

#Update SiteScore Field
count = 0
with arcpy.da.UpdateCursor(os.path.join(outpath,'Points_Polygons_Joined.shp'), 'SiteScore') as cursor:
     for row in cursor:
         row[0] = SiteScore[count]
         count += 1
         cursor.updateRow(row)
print 'Site_Score field has been updated'
'''
**********************[[[[[[]]]]]]**********************************************************************
'''

print 
print 
print '*********************************************************************************'
print 'PART 2'        
#Part 2 BLM Conservation vs BLM Oil, Gas and Coal         
#Finding the company which leases the most bml land for energy extraction for oil and gas, and coal
def searchCursor1(shapefile):
    countList=[]
    
    for i,elem in enumerate(shapefile):
        count=0
        with arcpy.da.SearchCursor(os.path.join(outpath,elem),['SHAPE@AREA']) as cursor:
            for row in cursor:
                count+=int(row[0])
        countList.append(count)
    return countList

def deletion(shapefile):
    for i in shapefile:
        if arcpy.Exists(os.path.join(outpath,i))==True:
            arcpy.Delete_management(i)

areaOfCEC='BLM_CO_ACEC_20220324.shp' #areas of critical environmental concern
wildChar='BLM_CO_LWC_20220324.shp' # Lands with wilderness characteristics
NM_and_NC='BLM_CO_NM_NCA_20220324.shp' # National monuments and national conservation areas
#trails='national_scenic_and_historic_trails.shp' #National scenic and historic trails
recSites='BLM_CO_RECS_SITES_20220324.shp' #Recreation sites
#rivers='wild_and_scenic_rivers.shp' #wild and scenic rivers
wilderness='BLM_CO_WILD_20211213.shp' #wilderness areas
wildStudy='BLM_CO_WSA_20211213.shp' #wildernes study areas

#energy leased areas
coal='BLM_CO_COAL_LEASES_20220317.shp' # colorado coal lease on BLM land
oilGas='BLM_CO_OIL_GAS_LEASES_20220316.shp' #colorado oil and gas leases on BLM land
oilShale='BLM_CO_OIL_SHALE_LEASES_20211208.shp' #colorado oil shale leases on BLM land

list1 = [coal,oilGas]
list2 = ['\coal','\oilgas']
list3 = ['coal','oil and gas']
count = 0
for a in list1:
    arcpy.conversion.TableToExcel(a,list2[count]+'_attribute.xls')
    df = pd.read_excel(env.workspace+list2[count]+'_attribute.xls')
    df2= df.groupby('NAME_1')['CASE_ACRES'].sum()
    df3= df2.sort_values(ascending=False)
    print 'Top three companies which leases the most BLM land for',list3[count],'extraction are:'
    print 'Company Name:',df3.index[0]
    print 'Total area:',df3[0],'Acres'
    print 'Company Name:',df3.index[1]
    print 'Total area:',df3[1],'Acres'
    print 'Company Name:',df3.index[2]
    print 'Total area:',df3[2],'Acres'
    print 
    count = count+1
  

#conservation and protected lands
conservationList=[areaOfCEC,wildChar,NM_and_NC,recSites,wilderness,wildStudy]
energyList=[coal,oilGas,oilShale]    

#deletes shapefiles
shapefileList=['unionEnergy.shp','all.shp','coal.shp','oilGas.shp','oilShale.shp','oilGas_buff500m.shp','oilGas_buff500_clipped.shp','mergedCons.shp']



            
deletion(shapefileList)
        
#union  areas
#unionConservation=arcpy.analysis.Union(conservationList,os.path.join(outpath,'unionConv')) 
unionEnergy=arcpy.analysis.Union(energyList,os.path.join(outpath,'unionEnergy'))
#oilGasUnion=arcpy.analysis.Union([oilGas,unionConservation],os.path.join(outpath,'oilGasUnion'))
mergedCons=arcpy.management.Merge(conservationList,os.path.join(outpath,'mergedCons'))


    
energyList.insert(0,unionEnergy)


#intersection
shapeNameList=['all','coal','oilGas','oilShale']
for i,elem in enumerate(energyList):
    arcpy.analysis.Intersect([os.path.join(outpath,'mergedCons.shp'),elem],os.path.join(outpath,shapeNameList[i]))
    

#Find out total area of conservation areas taking into account overlap
totalconservationArea=searchCursor1(['mergedcons.shp'])
print('The total amount of conservations area is '+str('{:,}'.format(totalconservationArea[0]))+' meters squared')
print('')

#percentage of each energy lease area in conservation areas
#need to make them shapefiles for the functions
shapeNameListShape=[]
for name in shapeNameList:
    name=name+'.shp'
    shapeNameListShape.append(name)
    
allAreas=searchCursor1(shapeNameListShape)

for i in range(len(allAreas)):
    print('The amount of '+shapeNameList[i]+' leased area in all conservation area is '+str('{:,}'.format(allAreas[i]))+' meters squared')
    print('This is '+ str(round(float(allAreas[i])/float(int(totalconservationArea[0]))*100,3))+'% of all conservation area')
    print('')

#amount of conservation land surrounding energy leased sites
arcpy.analysis.Buffer(oilGas, os.path.join(outpath,'oilGas_buff500f.shp'),'500 feet')
arcpy.analysis.Clip(os.path.join(outpath,'oilGas_buff500f.shp'),os.path.join(outpath,'mergedCons.shp'),os.path.join(outpath,'oilGas_buff500f_clipped.shp'))

buffArea=searchCursor1([os.path.join(outpath,'oilGas_buff500f_clipped.shp')])

print('Using a 500 meter buffer around oilGas energy leased sites, within 500 meters of the sites there is '+str('{:,}'.format(buffArea[0]))+' meters squared conservation areas')
print('This is ' +str(round(float(buffArea[0])/float(int(totalconservationArea[0]))*100,3))+'% of all conservation sites')
        