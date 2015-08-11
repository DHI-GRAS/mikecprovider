# -*- coding: utf-8 -*-
"""
/***************************************************************************
 mikecutils
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
from PyQt4.QtCore import *
from PyQt4 import QtGui, QtCore
import os
import re
import subprocess
from qgis.gui import QgsCredentialDialog


class mikecUtils:

    # base key for QSettings
    baseKey = "/MIKEC/connections/"

    @staticmethod
    def tr(string, context=''):
        if context == '':
            context = "mikecProvider"
        return QCoreApplication.translate(context, string)
        
    @staticmethod
    def getPgLogin(host, port, database, workspace, username, password):
        # The login details to the database are for now hardcoded and the same for all databases.
        # However the function definition is kept in case it is required in the future. 
        return "admin", "secretadmin"
    
    @staticmethod
    # Run the mc2qigs utility program
    def run_mc2qgis(mc2qgisCmd, showErrorBox = True):
        mc2qgisCmd = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mc2qgis", "mc2qgis.exe ") + mc2qgisCmd
        
        # Then run it
        out = ""
        proc = subprocess.Popen(
           mc2qgisCmd,
           shell=True,
           stdout=subprocess.PIPE,
           stdin=open(os.devnull),
           stderr=subprocess.STDOUT,
           universal_newlines=True,
           )
        for line in iter(proc.stdout.readline, ''):
            out = out + line
        proc.wait()
        
        if showErrorBox and proc.returncode != 0:
            QtGui.QMessageBox.information( None,
                                            mikecUtils.tr( "Connection failed" ),
                                            mikecUtils.tr( "Connection failed for the following reason: \n\n"+out
                                                            +"\nCheck settings and try again.\n\n" ) )
            
        return proc.returncode, out
    
    @staticmethod
    # Import the raster layer to MIKE C database
    def importRasterLayer(connection, rasterPath, group):
        # Prepare and run the mc2qgis command
        mc2qgisCmd = '-c "database='+connection["database"]+';host='+connection["host"]+';port='+str(connection["port"])+';dbflavour=PostgreSQL"'
        mc2qgisCmd = mc2qgisCmd +' -u '+connection["username"]+' -p '+connection["password"]+' -w '+connection["workspace"]
        mc2qgisCmd = mc2qgisCmd+" -v addtif@"+rasterPath+"@"+group
        returncode, output = mikecUtils.run_mc2qgis(mc2qgisCmd)

        if returncode != 0:
            return False
        else:
            return True
    
    @staticmethod
    # Change the layer name in MIKE C database
    def changeLayerName(mcConnectionName, uri, newName):
        
        # The password and username required for mc2qgis are not the database password and username 
        # stored in URI but the MC connection password and username stored in MC connection settings
        settings = QtCore.QSettings()
        password = settings.value(mikecUtils.baseKey + mcConnectionName + "/password")
        username = settings.value(mikecUtils.baseKey + mcConnectionName + "/username")
        
        # Ask for username/password if not provided
        if not (username and password):
            credentialDialog = QgsCredentialDialog()
            ok, newUsername, newPassword = credentialDialog.request('MIKE C', username, password, '')
            if ok:
                username = newUsername
                password = newPassword
            else:
                QtGui.QMessageBox.information( None,
                                            mikecUtils.tr( "Name not changed in the database" ),
                                            mikecUtils.tr( "Username or password not provided" ) )
                return False
        
        # Create and call mc2qgis command
        mc2qgisCmd = '-c "database='+uri.database()+';host='+uri.host()+';port='+uri.port()+';dbflavour=PostgreSQL"'
        mc2qgisCmd = mc2qgisCmd +' -u '+username+' -p '+password+' -w '+uri.schema()
        mc2qgisCmd = mc2qgisCmd+' -v changename@"'+uri.table()+'"@"'+newName+'"'
        returncode, _ = mikecUtils.run_mc2qgis(mc2qgisCmd)

        if returncode != 0:
            return False
        else:
            return True     
    
    @staticmethod
    # Get the information about MIKE C layers from mc2qigs utility program
    def getMikecLayersInfo(host, port, database, workspace, username, password):
        
        # Prepare and run the mc2qgis command
        mc2qgisCmd = '-c "database='+database+';host='+host+';port='+str(port)+';dbflavour=PostgreSQL"'
        mc2qgisCmd = mc2qgisCmd +' -u '+username+' -p '+password+' -w '+workspace+' -v list'
        returncode, output = mikecUtils.run_mc2qgis(mc2qgisCmd)

        if returncode != 0:
            return None
    
        # And extract information from the output file
        layerInfo = None
        layersInfoList = []        
        
        for line in output.split('\n'):
            if ("[FeatureClass]" in line) or ("[Raster]" in line):
                if layerInfo:
                    layersInfoList.append(layerInfo)
                layerInfo = {"Name":"", "Table":"", "SRID":"", "Path":"", "Keywords":""}
            else:
                tokens = re.split(r'\s+', line.lstrip().rstrip(), 1)
                if len(tokens)==2:
                    layerInfo[tokens[0]] = tokens[1]
        
        if layerInfo:
            layersInfoList.append(layerInfo)
            
        return layersInfoList
    
    @staticmethod
    def tempFolder():
        tempDir = os.path.join(unicode(QDir.tempPath()))
        if not QDir(tempDir).exists():
            QDir().mkpath(tempDir)
    
        return unicode(os.path.abspath(tempDir))      