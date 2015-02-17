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
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import os
from db_manager.db_plugins.postgis import connector
from db_manager.db_plugins.plugin import ConnectionError
from mikecConnectionDialog import mikecConnectionDialog
from mikecUtils import mikecUtils as utils
from mikecTableModel import mikecTableModel

from PyQt4 import QtGui, uic, QtCore
from qgis.core import *
from qgis.gui import QgsCredentialDialog

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'mikec_dbsourceselector_dialog_base.ui'))


class mikecProviderDialog(QtGui.QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(mikecProviderDialog, self).__init__(parent)

        self.setupUi(self)
        
        self.layersModel = mikecTableModel()
        self.layersView.setModel(self.layersModel)
        self.layersView.setSortingEnabled(True)
        self.layersView.verticalHeader().hide()
        self.layersView.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows);
        self.setLayersView()
        
        self.populateConnectionList()
        
        # Hide widgets instead of removing them since they might be used in the future
        self.mSearchGroupBox.hide()
        self.btnLoad.hide()
        self.btnSave.hide()
        self.buttonBox.button(QtGui.QDialogButtonBox.Help).hide()
        
        self.btnOpen = self.buttonBox.button(QtGui.QDialogButtonBox.Open)
        self.btnOpen.setDisabled(True)
        self.btnOpen.clicked.connect(self.loadLayer)
        
        self.btnConnect.clicked.connect(self.populateLayersView)
        self.btnNew.clicked.connect(self.newConnectionDialog)
        self.btnEdit.clicked.connect(self.editConnectionDialog)
        self.btnDelete.clicked.connect(self.deleteConnection)
        self.cmbConnections.currentIndexChanged.connect(self.setSelectedConnection)
        
        # Database connection
        self.connection = None
    
    def setLayersView(self):
        self.layersModel.clear()
        self.layersModel.setHeader()
        # Some columns are for storying information and not for showing
        for column, width in enumerate(self.layersModel.getColumnWidths()):
            if width > 0:
                self.layersView.setColumnWidth(column, width)
            else: 
                self.layersView.setColumnHidden(column, True)
    
    # Connect both directly to PostGIS databse and through mc2qigs utility program
    # and list tables found in both connections. Both connections are needed since
    # they provide different information
    def populateLayersView(self):
        
        # Get connection details of the currently selected connection
        settings = QtCore.QSettings()
        key = utils.baseKey + self.cmbConnections.currentText()
        host = settings.value(key + '/host')
        database = settings.value(key + '/database')
        port = settings.value(key + '/port')
        schema = settings.value(key + '/workspace')
        username = settings.value(key + '/username')
        password = settings.value(key + '/password')
        
        # Ask for username/password if not provided
        if not (username and password):
            credentialDialog = QgsCredentialDialog()
            ok, newUsername, newPassword = credentialDialog.request('MIKE C', username, password, '')
            if ok:
                username = newUsername
                password = newPassword
            else:
                return
            
        originalText = self.btnConnect.text()
        self.btnConnect.setText(utils.tr("Connecting..."))
        self.btnConnect.setEnabled(False)
        self.btnConnect.repaint()
        
        # Reset the layers table
        self.setLayersView()
        
        # Get the postgis username and password from the MIKEC utility
        pgUsername, pgPassword = utils.getPgLogin(host, port, database, schema, username, password)
        
        # Retrieve the geotables from postgis database
        try:
            self.uri = QgsDataSourceURI()
            self.uri.setConnection(host, port, database, pgUsername, pgPassword)
            self.connection = connector.PostGisDBConnector(self.uri)
            vectorTablesList = self.connection.getVectorTables(schema)
            rasterTablesList = self.connection.getRasterTables(schema)
            geotablesList = vectorTablesList + rasterTablesList
        except ConnectionError:
            QtGui.QMessageBox.information( self,
                                            utils.tr( "Connection failed" ),
                                            utils.tr( "Connection failed - Check settings and try again.\n\n" ) )
            self.connection = None

        if self.connection:
            # Get additional table information from mc2qgis utility
            layersInfoList = utils.getMikecLayersInfo(host, port, database, schema, username, password)
        
        # Populate the layers view with tables for which information is present in both connections
        if self.connection and layersInfoList:
            for geotable in geotablesList:
                layerProperty = {}
                layerProperty['table_name'] = geotable[1]
                layerInfo = next((item for item in layersInfoList if item["Table"] == layerProperty['table_name']), None)
                if layerInfo:
                    layerProperty['layer_name'] = layerInfo["Name"]
                    layerProperty['table_path'] = layerInfo["Path"]
                    layerProperty['table_keywords'] = layerInfo["Keywords"]
                else:
                    continue
                
                if geotable in vectorTablesList:
                    layerProperty['table_type'] = geotable[9]
                    layerProperty['table_srid'] = str(geotable[11])
                else:
                    layerProperty['table_type'] = "RASTER"
                    layerProperty['table_srid'] = str(geotable[13])
                layerProperty['geometry_column'] = geotable[8]
                layerProperty['table_schema'] = geotable[2]
                
                self.layersModel.addTableEntry(layerProperty)
                self.btnOpen.setDisabled(False)
                
                
        self.btnConnect.setText(originalText)
        self.btnConnect.setEnabled(True)
    
    # Slot for performing action when the Load button is clicked   
    def loadLayer(self):
        
        if not self.layersView.selectionModel().selection().indexes():
            QtGui.QMessageBox.information( self, utils.tr( "Select Table" ), utils.tr( "You must select a table in order to add a layer." ) )
        
        loadedRows = []
        for index in self.layersView.selectionModel().selection().indexes():
            
            # Load each table row only once
            if index.row() in loadedRows:
                continue
            else:
                loadedRows.append(index.row())
            
            # Prepare layer URI  
            # Set database schema, table name, geometry column and optionally
            # subset (WHERE clause)
            uriInfo = self.layersModel.getLayerUriInfo( index )
            self.uri.setDataSource(uriInfo['table_schema'], uriInfo['table_name'], uriInfo['geometry_column'], "")
   
            # Add to QGIS
            if uriInfo["spatial_type"] == "RASTER":
                gdalUri = "PG: dbname="+self.uri.database()+" host="+self.uri.host()+" user="+self.uri.username()
                gdalUri = gdalUri +" password="+self.uri.password()+" port="+self.uri.port()+" mode=2"
                gdalUri = gdalUri +" schema="+self.uri.schema()+" column="+self.uri.geometryColumn()
                gdalUri = gdalUri +" table="+self.uri.table() 
                layer = QgsRasterLayer(gdalUri, uriInfo['layer_name'], "gdal")
            else:
                layer = QgsVectorLayer(self.uri.uri(), uriInfo['layer_name'], "postgres")
            QgsMapLayerRegistry.instance().addMapLayer(layer)
            
        if not self.mHoldDialogOpen.isChecked():
            self.closeDialog()
       
        
    def newConnectionDialog(self):
        connectionDialog = mikecConnectionDialog(self, None)
        connectionDialog.exec_()
        self.populateConnectionList()

    def editConnectionDialog(self):
        connectionDialog = mikecConnectionDialog(self, self.cmbConnections.currentText())
        connectionDialog.exec_()

    def populateConnectionList(self):
        settings = QtCore.QSettings()
        settings.beginGroup( "/" + utils.baseKey )
        keys = settings.childGroups()
        self.cmbConnections.clear()
        for key in keys:
            self.cmbConnections.addItem( key );

        settings.endGroup()
        self.setConnectionListPosition()
        
        self.btnEdit.setDisabled( self.cmbConnections.count() == 0 );
        self.btnDelete.setDisabled( self.cmbConnections.count() == 0 );
        self.btnConnect.setDisabled( self.cmbConnections.count() == 0 );
        self.cmbConnections.setDisabled( self.cmbConnections.count() == 0 );
        
    def setConnectionListPosition(self):
        settings = QtCore.QSettings()
        # If possible, set the item currently displayed database
        toSelect = settings.value( utils.baseKey +"selected" )
        # Does toSelect exist in cmbConnections?
        isSet = False
        for i in range (self.cmbConnections.count()):
            if ( self.cmbConnections.itemText( i ) == toSelect ):
                self.cmbConnections.setCurrentIndex( i )
                isSet = True
                break
        # If we couldn't find the stored item, but there are some,
        # default to the last item (this makes some sense when deleting
        # items as it allows the user to repeatidly click on delete to
        # remove a whole lot of items).
        if ( not isSet and self.cmbConnections.count() > 0 ):
            # If toSelect is null, then the selected connection wasn't found
            # by QSettings, which probably means that this is the first time
            # the user has used qgis with database connections, so default to
            # the first in the list of connetions. Otherwise default to the last.
            if ( not toSelect ):
                self.cmbConnections.setCurrentIndex( 0 );
            else:
                self.cmbConnections.setCurrentIndex( self.cmbConnections.count() - 1 )

    def setSelectedConnection(self, text):
        settings = QtCore.QSettings()
        settings.setValue( utils.baseKey +"selected", self.cmbConnections.currentText() )
        
    def deleteConnection(self):
        settings = QtCore.QSettings()
        key = utils.baseKey + self.cmbConnections.currentText()
        msg = utils.tr( "Are you sure you want to remove the %s connection and all associated settings?" ) % (self.cmbConnections.currentText() ) 
        result = QtGui.QMessageBox.information( self, utils.tr( "Confirm Delete" ), msg, QtGui.QMessageBox.Ok | QtGui.QMessageBox.Cancel );
        if ( result == QtGui.QMessageBox.Ok ):
            settings.remove( key + "/host" )
            settings.remove( key + "/database" )
            settings.remove( key + "/username" )
            settings.remove( key + "/password" )
            settings.remove( key + "/saveUsername" )
            settings.remove( key + "/savePassword" )
            settings.remove( key + "/port" )
            settings.remove( key + "/workspace" )
            settings.remove( key )
            self.cmbConnections.removeItem( self.cmbConnections.currentIndex() ) # populateConnectionList();
            self.setConnectionListPosition()
            
    def closeDialog(self):
        self.connection = None
        self.setLayersView()
        self.btnOpen.setDisabled(True)
        self.close()
        
    def reject(self):
        self.closeDialog()
        super(mikecProviderDialog, self).reject()
        