# -*- coding: utf-8 -*-
"""
/***************************************************************************
 mikecproviderDialog
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
 *   This program is free software you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***
 
 """
 
 
from PyQt4 import QtGui, uic, QtCore
from mikecUtils import mikecUtils as utils

# QT model for holding layers' information. 
# Some of the columns might be hidden in the GUI.
class mikecTableModel(QtGui.QStandardItemModel):
    
    def __init__(self):
        super(mikecTableModel, self).__init__()
         
    def addTableEntry(self, layerProperty):
        
        childItemList = []
        childItemList.append(QtGui.QStandardItem(layerProperty['layer_name']))
        childItemList.append(QtGui.QStandardItem(layerProperty['table_path']))
        childItemList.append(QtGui.QStandardItem(layerProperty['table_type']))
        childItemList.append(QtGui.QStandardItem(layerProperty['table_srid']))
        childItemList.append(QtGui.QStandardItem(layerProperty['table_keywords']))
        childItemList.append(QtGui.QStandardItem(layerProperty['table_name']))
        childItemList.append(QtGui.QStandardItem(layerProperty['table_schema']))
        childItemList.append(QtGui.QStandardItem(layerProperty['geometry_column']))
        
        self.invisibleRootItem().appendRow(childItemList)
        
    def setHeader(self):
        
        headerLabels = []
        headerLabels.append(utils.tr( "Name" ))
        headerLabels.append(utils.tr( "Path"))
        headerLabels.append(utils.tr( "Spatial Type"))
        headerLabels.append(utils.tr( "SRID"))
        headerLabels.append(utils.tr( "Keywords"))
        headerLabels.append(utils.tr( "orig_name" ))
        headerLabels.append(utils.tr( "schema" ))
        headerLabels.append(utils.tr( "geom_column" ))
        self.setHorizontalHeaderLabels(headerLabels)
        
        
    def getLayerUriInfo(self, index):
        
        uriInfo = {}
        
        if not index: 
            return None
        
        uriInfo["layer_name"] = index.sibling( index.row(), 0 ).data()
        uriInfo["spatial_type"] = index.sibling( index.row(), 2 ).data()
        uriInfo["table_name"] = index.sibling( index.row(), 5 ).data()
        uriInfo["table_schema"] = index.sibling( index.row(), 6 ).data()
        uriInfo["geometry_column"] = index.sibling( index.row(), 7 ).data()
        
        return uriInfo
    
    # List of columns which are storying information but are not for showing in the GUI
    def getColumnWidths(self):
        return[155, 160, 90, 45, 100, 0, 0, 0]

        