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
from PyQt4 import QtGui
import os
import re
import subprocess



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