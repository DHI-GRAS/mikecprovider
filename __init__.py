# -*- coding: utf-8 -*-
"""
/***************************************************************************
 mikecprovider
                                 A QGIS plugin
 MIKE C data provider
                             -------------------
        begin                : 2015-02-05
        copyright            : (C) 2015 by DHI GRAS
        email                : rmgu@dhigras.com
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load mikecprovider class from file mikecprovider.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .mikec_provider import mikecprovider
    return mikecprovider(iface)
