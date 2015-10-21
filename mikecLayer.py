# -*- coding: utf-8 -*-
"""
/***************************************************************************
 mikecLayer
                                 A QGIS plugin
 MIKE C data provider
                             -------------------
        begin                : 2015-02-05
        git sha              : $Format:%H$
        copyright            : (C) 2015 by DHI GRAS
        email                : rmgu@dhigras.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
import re
import os
import uuid
from qgis.core import *
from qgis.gui import QgsSublayersDialog
from processing.tools.system import tempFolder
from processing.tools import dataobjects
import processing

from mikecUtils import mikecUtils as utils

logger = lambda msg: QgsMessageLog.logMessage(msg, 'MIKE C Provider', 1)

class MikecLayer():
    
    def __init__(self, uri, layerName, layerType, mikecConnectionName, loadedLayers):
        
        self.uri = uri
        self.mikecConnectionName = mikecConnectionName
        self.addedFeaturesIds = []
        self.changedFeaturesIds = []
        self.loadedLayers = loadedLayers
        
        
        self.loadedLayers.append(self)
        
        #========================================
        # Add to QGIS
        
        # Rasters
        if layerType == "RASTER":
            gdalUri = "PG: dbname='"+self.uri.database()+"' host='"+self.uri.host()+"' user='"+self.uri.username()
            gdalUri = gdalUri +"' password='"+self.uri.password()+"' port="+self.uri.port()+" mode=1"
            gdalUri = gdalUri +" schema='"+self.uri.schema()+"' column='"+self.uri.geometryColumn()
            gdalUri = gdalUri +"' table='"+self.uri.table()+"'" 
            self.layer = QgsRasterLayer(gdalUri, layerName, "gdal")
            if self.layer and self.layer.dataProvider().name() == "gdal" and len(self.layer.subLayers()) > 1:
                self.layer = self.loadSubLayersVRT(self.layer, gdalUri)
        
            # Make slot connections
            self.layer.layerNameChanged.connect(self.layer_name_changed)
        
        # Vectors    
        else:
            print self.uri.uri()
            self.layer = QgsVectorLayer(self.uri.uri(), layerName, "postgres")
            
            # Make slot connections
            self.layer.editingStarted.connect(self.editing_started)
            self.layer.featureAdded.connect(self.feature_added)
            self.layer.attributeValueChanged.connect(self.attribute_value_changed)
            self.layer.geometryChanged.connect(self.geometry_changed)
            self.layer.featureDeleted.connect(self.feature_deleted)
            self.layer.featuresDeleted.connect(self.features_deleted)           
            self.layer.beforeCommitChanges.connect(self.before_commit_changes)
            self.layer.layerNameChanged.connect(self.layer_name_changed)
            self.layer.layerDeleted.connect(self.layer_deleted)
            
        # Display on canvas
        if self.layer:
            QgsMapLayerRegistry.instance().addMapLayer(self.layer)
        else:
            self.layer_deleted()
             
    
    # Function for loading sublayers of raster layers (rows of a table with GDAL PG mode = 1)
    # All the sublayers are loaded and combined in a GDAL VRT file so that to the user they look
    # like different bands of the same raster
    def loadSubLayersVRT(self, rl, gdalUri):
        layerName = rl.name()
        
        # List all of the sublayers in a format required by GDAL Build VRT
        inputFileList = ""
        for subLayer in rl.subLayers():
            subLayer = re.search("where=.*$", subLayer).group(0)
            subLayer = re.sub("(where=.*= )", "\g<1>\\'", subLayer)
            subLayer = re.sub("'$", "\\''", subLayer)
            inputFileList = inputFileList + gdalUri + " " + subLayer + ";"          
        inputFileList = inputFileList[:-1]
        
        options = {"INPUT":inputFileList, "RESOLUTION":0, "SEPARATE":True, "PROJ_DIFFERENCE":False, "OUTPUT": None}
        out = processing.runalg("gdalogr:buildvirtualraster", options) 
        dataobjects.resetLoadedLayers()
        if out:
            vrtLayer = QgsRasterLayer(out["OUTPUT"], layerName)
            return vrtLayer
        return None
        
    
    # THIS FUNCTION IS NO LONGER USED BUT IS KEPT IN CASE IT IS NEEDED IN THE FUTURE        
    # Function for loading sublayers of raster layers (rows of a table with GDAL PG mode = 1)
    # Displays the list of sublayers and the user can select which ones to load. Each sublayer is loaded as a 
    # separate raster
    def loadSubLayers(self, rl):
        tableContent = []
        subLayers = []
        subLayerNum = 0
        layerName = rl.name()
        # simplify raster sublayer name
        for subLayer in rl.subLayers():
            subLayer = re.sub("^.*where=", "", subLayer)
            subLayer.replace("'", "")
            subLayer.replace('"', "")      
            tableContent.append(str(subLayerNum)+"|"+subLayer)
            subLayers.append(subLayer) 
            subLayerNum = subLayerNum + 1
                    
        # Use QgsSublayersDialog to select sublayers to load
        chooseSublayersDialog = QgsSublayersDialog(QgsSublayersDialog.Gdal, "gdal") 
        chooseSublayersDialog.populateLayerTable( tableContent, "|" )
        chooseSublayersDialog.resize(500, chooseSublayersDialog.height())
        if chooseSublayersDialog.exec_():
            baseSourceStr = rl.source()
            # Enclose where statement in appropriate quotes
            for i in chooseSublayersDialog.selectionIndexes(): 
                subLayer = subLayers[i]
                subLayer = re.sub("= ", "= \\'", subLayer)
                subLayer = re.sub("'$", "\\''", subLayer)
                gdalStr = baseSourceStr + " where="+subLayer
                rl = QgsRasterLayer(gdalStr, layerName + '_'+subLayers[i])
                QgsMapLayerRegistry.instance().addMapLayer(rl)
    
    ###################################################################################
    # SLOTS            
    def editing_started(self):
        self.addedFeaturesIds = []
        self.changedFeaturesIds = []
        
    def feature_added(self, fid):
        if fid not in self.addedFeaturesIds: self.addedFeaturesIds.append(fid)
        
    def attribute_value_changed(self, fid, a, b):
        if fid not in self.changedFeaturesIds and fid not in self.addedFeaturesIds: self.changedFeaturesIds.append(fid)
    
    def geometry_changed(self, fid, a):
        if fid not in self.changedFeaturesIds and fid not in self.addedFeaturesIds: self.changedFeaturesIds.append(fid)
        
    def feature_deleted(self, fid):
        if fid in self.addedFeaturesIds: self.addedFeaturesIds.remove(fid)
        if fid in self.changedFeaturesIds: self.changedFeaturesIds.remove(fid)
        
    def features_deleted(self, fids):
        for fid in fids:
            if fid in self.addedFeaturesIds: self.addedFeaturesIds.remove(fid)
            if fid in self.changedFeaturesIds: self.changedFeaturesIds.remove(fid)
     
    def before_commit_changes(self):
        # Add id and version of new features 
        for fid in self.addedFeaturesIds:
            fl = self.layer.getFeatures(QgsFeatureRequest(fid))
            for f in fl:
                id_id = f.fieldNameIndex("id")
                version_id = f.fieldNameIndex("version")
                break
            self.layer.changeAttributeValue(fid, id_id, str(uuid.uuid1()))
            self.layer.changeAttributeValue(fid, version_id, str(uuid.uuid1()))
        
        # Update version of changed features
        for fid in self.changedFeaturesIds:
            fl = self.layer.getFeatures(QgsFeatureRequest(fid))
            for f in fl:
                version_id = f.fieldNameIndex("version")
                break
            self.layer.changeAttributeValue(fid, version_id, str(uuid.uuid1()))
        
        self.addedFeaturesIds = []
        self.changedFeaturesIds = []
                 
    
    def layer_name_changed(self):
        utils.changeLayerName(self.mikecConnectionName, self.uri, self.layer.name())
             
    def layer_deleted(self):
        self.loadedLayers.remove(self)       
        