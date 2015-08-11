# -*- coding: utf-8 -*-
"""
/***************************************************************************
 mikecImportRasterDialog
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
 ***************************************************************************/
"""

import os

from PyQt4 import QtGui, uic, QtCore
from qgis.core import QgsProject, QgsMapLayer, QgsRasterLayer

from PyQt4.QtCore import QSettings
from PyQt4.QtGui import QFileDialog, QMessageBox, QDialogButtonBox

from mikecUtils import mikecUtils as utils

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'mikec_importRaster_dialog_base.ui'))


class mikecImportRasterDialog(QtGui.QDialog, FORM_CLASS):

    def __init__(self, connection, parent=None):
        """Constructor."""
        super(mikecImportRasterDialog, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        
        for (name, value) in self.getRasterLayers():
            self.cmbText.addItem(name, value)
        
        self.btnSelect.clicked.connect(self.showSelectionDialog)
    
        self.connection = connection
    
    def accept(self):
        layerPath = self.cmbText.itemData(self.cmbText.currentIndex())
        group = self.lineGroup.displayText()
        
        btnOk = self.buttonBox.button(QDialogButtonBox.Ok)
        originalText = btnOk.text()
        btnOk.setText(utils.tr("Importing..."))
        btnOk.setEnabled(False)
        btnOk.repaint()
        
        res = utils.importRasterLayer(self.connection, layerPath, group)
        
        btnOk.setText(originalText)
        btnOk.setEnabled(True)
        
        if not res:
            QMessageBox.warning( self,
               utils.tr( "Could not import layer" ),
               utils.tr( "Could not import layer %s.") % (layerPath),
               QtGui.QMessageBox.Ok)
        else:
            super(mikecImportRasterDialog, self).accept()
                
    
    # List all TIF layers currently loaded in QGIS     
    def getRasterLayers(self, sorting=True):
        layers = QgsProject.instance().layerTreeRoot().findLayers()
        raster = []
    
        for layer in layers:
            mapLayer = layer.layer()
            if mapLayer.type() == QgsMapLayer.RasterLayer:
                
                if mapLayer.providerType() == 'gdal' and mapLayer.source().lower().endswith(".tif"):  # only TIFF file-based layers
                    raster.append((mapLayer.name(), mapLayer.source()))
        if sorting:
            return sorted(raster,  key=lambda layer: layer[0].lower())
        else:
            return raster
        
    # Pick a TIFF layer from file system
    def showSelectionDialog(self):
        settings = QSettings()
        text = unicode(self.cmbText.itemData(self.cmbText.currentIndex()))
        if os.path.isdir(text):
            path = text
        elif os.path.isdir(os.path.dirname(text)):
            path = os.path.dirname(text)
        elif settings.contains(utils.baseKey+'/LastInputPath'):
            path = unicode(settings.value(utils.baseKey+'/LastInputPath'))
        else:
            path = ''

        filename = unicode(QFileDialog.getOpenFileName(self, self.tr('Select file'),
            path, self.tr('TIFF files (*.tif)')))
        if filename:
            layer = QgsRasterLayer(filename)
            if layer.providerType() == 'gdal' and layer.source().lower().endswith(".tif"):
                settings.setValue(utils.baseKey+'/LastInputPath', os.path.dirname(unicode(filename)))
                self.cmbText.addItem(filename, filename)
                self.cmbText.setCurrentIndex(self.cmbText.count() - 1)
        