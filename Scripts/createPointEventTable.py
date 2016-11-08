"""
Create point event table, suitable for input to Locate Features Along Route tool

The Event Table has two fields:
Route Identifier Field - The field containing values that indicate the route
 on which each event is located. This field can be numeric or character.
The field type is derived from the Input Route Features
Measure Field - A field containing measure values. This field is numeric.
The value is populated from geometry.firstPoint.M to geometry.lastPoint.M
 stepping by measure_interval
"""
import os
import arcpy


def get_field(dataset, field_name):
    """ takes feature class and field name as input and
    return field object for the given field name"""
    return [f for f in arcpy.Describe(dataset).fields if f.name in field_name][0]


def frange(start, stop, step):
    """Range function that works with floats"""
    r = start
    while r < stop:
        yield r
        if step > 0:
            r += step
        else:
            r -= step


def create_point_event_table(in_routes, route_id_field_name, measure_interval, out_table):
    """
    Create point event table, suitable for input to Locate Features Along Route tool

    The output Event Table has two fields:
    Route Identifier Field - The field containing values that indicate the route
    on which each event is located. This field can be numeric or character.
    The field type is derived from the Input Route Features
    Measure Field - A field containing measure values. This field is numeric.
    The value is populated from geometry.firstPoint.M to geometry.lastPoint.M
    stepping by measure_interval
    """    
    # get infomation about the route_id field
    route_id_field = get_field(in_routes, route_id_field_name)
    route_id_field_type = route_id_field.type
    route_id_field_length = route_id_field.length

    # Create the output table
    path, name = os.path.split(out_table)
    arcpy.management.CreateTable(path, name)
    arcpy.management.AddField(out_table, route_id_field_name, route_id_field_type,
                                field_length=route_id_field_length)
    arcpy.management.AddField(out_table, 'Measure', "DOUBLE")

    # Populate event table using cursors
    search_fields = [route_id_field_name, "SHAPE@"]
    update_fields = [route_id_field_name, 'Measure']
    with arcpy.da.InsertCursor(out_table, update_fields) as icursor:
        with arcpy.da.SearchCursor(in_routes, search_fields) as cursor:
            for row in cursor:
                line = row[1]
                first_measure = float(line.firstPoint.M)
                last_measure = float(line.lastPoint.M)
                for measure in frange(first_measure, last_measure, measure_interval):
                    icursor.insertRow((row[0], measure))

    return out_table                    

class CreatePointEventTable(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Create Point Events at Intervals"
        self.description = "Create point event table, suitable for input to Locate Features Along Route tool."
        self.category = 'Build Event Table'
        self.canRunInBackground = True

    def getParameterInfo(self):
        """Define parameter definitions"""
        in_routes = arcpy.Parameter(
            displayName='Input Route Features',
            name='in_routes',
            datatype='GPFeatureLayer',
            parameterType='Required',
            direction='Input')
        in_routes.filter.list = ["Polyline"]

        route_id_field = arcpy.Parameter(
            displayName='Route Identifier Field',
            name='route_id_field',
            datatype='Field',
            parameterType='Required',
            direction='Input')

        route_id_field.filter.list = ['Short', 'Long', 'Text']
        route_id_field.parameterDependencies = [in_routes.name]

        measure_interval = arcpy.Parameter(
            displayName='Interval to create events',
            name='measure_interval',
            datatype='GPDouble',
            parameterType='Required',
            direction='Input')
        measure_interval.value = 10.0

        out_table = arcpy.Parameter(
            displayName='Output Event Table',
            name='out_table',
            datatype='DETable',
            parameterType='Required',
            direction='Output')

        params = [in_routes, route_id_field, measure_interval, out_table]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        in_routes = parameters[0].valueAsText
        route_id_field_name = parameters[1].valueAsText
        measure_interval = parameters[2].value
        out_table = parameters[3].valueAsText

        create_point_event_table(in_routes, route_id_field_name, measure_interval, out_table)
        return
