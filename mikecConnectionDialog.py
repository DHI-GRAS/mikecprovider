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
 ***************************************************************************/
"""

import os

from PyQt4 import QtGui, uic, QtCore

from mikecUtils import mikecUtils as utils

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'mikec_connection_dialog_base.ui'))


class mikecConnectionDialog(QtGui.QDialog, FORM_CLASS):
    
    # Logic based on providers/postgres/qgspgnewconnection.cpp
    def __init__(self, parent=None, connName = None):
        """Constructor."""
        super(mikecConnectionDialog, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        
        self.btnConnect.clicked.connect(self.testConnection)
        self.btnWorkspace.clicked.connect(self.listWorkspaces)
        #self.cbxWorkspace.activated.connect(self.workspacesListed)
                
        if connName:
            # populate the dialog with the information stored for the connection
            # populate the fields with the stored setting parameters
            settings = QtCore.QSettings()
            key = utils.baseKey+connName
            
            self.txtName.setText( connName )
            self.txtHost.setText( settings.value(key + '/host') )
            self.txtPort.setText( settings.value(key + '/port') )
            self.txtDatabase.setText( settings.value(key + '/database') )
            #self.cbxSLLmode.setItemText(self.cbxSLLmode.findData(settings.value(key + '/sslMode', QgsDataSourceURI.SSLprefer).toInt()))
            if settings.value( key + "/saveUsername" ) == "true":
                self.txtUsername.setText( settings.value( key + "/username" ) )
                self.chkStoreUsername.setChecked( True )
            if settings.value( key + "/savePassword" ) == "true":
                self.txtPassword.setText( settings.value( key + "/password" ) )
                self.chkStorePassword.setChecked( True )
            self.cbxWorkspace.addItem(settings.value( key + "/workspace" ) )
        else:
            self.cbxWorkspace.addItem("Workspace1")
            
        self.originalConnName = connName
        
        self.listingWorkspaces = False
            
    def accept(self):
        settings = QtCore.QSettings()
        baseKey = utils.baseKey
        connName = self.txtName.text()
        
        settings.setValue(baseKey+"selected", connName)
        
        if (self.chkStorePassword.isChecked() and 
           QtGui.QMessageBox.question( self,
           utils.tr( "Saving passwords" ),
           utils.tr( "WARNING: You have opted to save your password. It will be stored in plain text in your project files and in your home directory on Unix-like systems, or in your user profile on Windows. If you do not want this to happen, please press the Cancel button.\n" ),
           QtGui.QMessageBox.Ok | QtGui.QMessageBox.Cancel ) == QtGui.QMessageBox.Cancel ):
            return
            
        # warn if entry was renamed to an existing connection
        if (( not self.originalConnName or self.originalConnName != connName ) and
           ( settings.contains( baseKey + connName + "/host" ) ) and
           QtGui.QMessageBox.question( self,
           utils.tr( "Save connection" ),
           utils.tr( "Should the existing connection %s be overwritten?") % (connName),
           QtGui.QMessageBox.Ok | QtGui.QMessageBox.Cancel ) == QtGui.QMessageBoxCancel ):
            return
        
        # on rename delete the original entry first
        if ( self.originalConnName and self.originalConnName != connName ):
            settings.remove( baseKey + self.originalConnName )

        baseKey = baseKey + connName
        settings.setValue( baseKey + "/host", self.txtHost.text() )
        settings.setValue( baseKey + "/port", self.txtPort.text() )
        settings.setValue( baseKey + "/database", self.txtDatabase.text() )
        settings.setValue( baseKey + "/username", self.txtUsername.text() if self.chkStoreUsername.isChecked() else "" )
        settings.setValue( baseKey + "/password", self.txtPassword.text() if self.chkStorePassword.isChecked() else "" )
        settings.setValue( baseKey + "/saveUsername", "true" if self.chkStoreUsername.isChecked() else "false" )
        settings.setValue( baseKey + "/savePassword", "true" if self.chkStorePassword.isChecked() else "false" )
        settings.setValue( baseKey + "/workspace", self.cbxWorkspace.currentText() )

        super(mikecConnectionDialog, self).accept()
        
    def testConnection(self):
        
        originalText = self.btnConnect.text()
        self.btnConnect.setText(utils.tr("Connecting..."))
        self.btnConnect.setEnabled(False)
        self.btnConnect.repaint()
        
        output = utils.getMikecLayersInfo(self.txtHost.text(), self.txtPort.text(), self.txtDatabase.text(),
                           self.cbxWorkspace.currentText(), self.txtUsername.text(), self.txtPassword.text())           

        if output:
            QtGui.QMessageBox.information( self,
                                           utils.tr( "Test connection" ),
                                           utils.tr( "Connection to %s was successful" ) % (self.txtDatabase.text()) )

        self.btnConnect.setText(originalText)
        self.btnConnect.setEnabled(True)
      
      
    def listWorkspaces(self):
        
        origText = self.cbxWorkspace.currentText()
        self.cbxWorkspace.clear()
        self.cbxWorkspace.addItem(utils.tr("Loading..."))
        self.cbxWorkspace.repaint()
        
        mc2qgisCmd = '-c "database='+self.txtDatabase.text()+';host='+self.txtHost.text()+';port='+self.txtPort.text()+';dbflavour=PostgreSQL"'
        mc2qgisCmd = mc2qgisCmd +' -v workspaces'
        returncode, output = utils.run_mc2qgis(mc2qgisCmd)
        
        workspaceList = []
        keywordFound = False
        for line in output.split('\n'):
            if "[Workspaces]" in line:
                keywordFound = True
            else:
                if line.lstrip().rstrip():
                    workspaceList.append(line.lstrip().rstrip())
        
        self.cbxWorkspace.clear()
        if returncode == 0 and keywordFound and len(workspaceList) > 0:
            for workspace in workspaceList:
                self.cbxWorkspace.addItem(workspace)  
        self.cbxWorkspace.repaint()  
        
        for i in range(self.cbxWorkspace.count()):
            if origText == self.cbxWorkspace.itemText(i):
                self.cbxWorkspace.setCurrentIndex(i)
                break     
        