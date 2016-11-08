"""
The Additional Linear Referencing Tools provides a collection of geoprocessing tools
for working with linear referencing systems.

The toolbox is conveniently organized into
toolsets which define the general sequence of tasks accomplished by
the tools.

More information about linear referencing systems is available at
http://desktop.arcgis.com/en/arcmap/latest/manage-data/linear-referencing/what-is-linear-referencing.htm
"""
import sys
import os


# Tools are located in a subfolder called Scripts. Append to path
SCRIPTPATH = os.path.join(os.path.dirname(__file__), "Scripts")
sys.path.append(SCRIPTPATH)

# Do not compile .pyc files for the tool modules.
sys.dont_write_bytecode = True

# Import the tool
from createPointEventTable import CreatePointEventTable
from createLineEventTable import CreateLineEventTable
from createRouteByLength import CreateRouteByLength
from createPointsAlongLine import PointsAlongLine
from stationPointsAndCrossSections import StationPointsAndCrossSections

del SCRIPTPATH

class Toolbox(object):
    """ArcGIS Python Toolbox - Additional Linear Referencing Tools"""
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = 'Additional Linear Referencing Tools'
        self.alias = 'alr'

        # List of tool classes associated with this toolbox
        self.tools = [CreatePointEventTable,
                      CreateLineEventTable,
                      CreateRouteByLength,
                      PointsAlongLine,
                      StationPointsAndCrossSections]
