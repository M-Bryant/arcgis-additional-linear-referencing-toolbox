"""
create_line_event_table.py
Create an linear event table, suitable for input to Locate Features Along Route tool.
The Event Table has three fields:
Route Identifier Field-The field containing values that indicate the route on which each event is located.  This field can be numeric or character.
The field type is derived from the Input Route Features
From-Measure Field-A field containing measure values. This field must be numeric.
The value is extracted from Input Route geometry firstPoint.M
To-Measure Field-A field containing measure values. This field must be numeric.
The value is extracted from from Input Route geometry lastPoint.M

Extracting the from and To measures from the geomtry ensures that the event table covers the length of the route

"""
import os
import arcpy


def get_field(dataset, field_name):
    """ takes feature class and field name as input and
    return field object for the given field name"""
    return [f for f in arcpy.Describe(dataset).fields if f.name in field_name][0]


class CreateLineEventTable(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Create Line Events Covering Routes"
        self.description = 'Create linear event table, suitable for input to Locate Features Along Route tool.'
        self.category = 'Build Event Table'
        self.canRunInBackground = False

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

        out_table = arcpy.Parameter(
            displayName='Output Event Table',
            name='out_table',
            datatype='DETable',
            parameterType='Required',
            direction='Output')

        params = [in_routes, route_id_field, out_table]
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
        out_table = parameters[2].valueAsText

        # get infomation about the route_id field
        route_id_field = get_field(in_routes, route_id_field_name)
        route_id_field_type = route_id_field.type
        route_id_field_length = route_id_field.length

        # Create the output table
        path, name = os.path.split(out_table)
        arcpy.management.CreateTable(path, name)
        arcpy.management.AddField(out_table, route_id_field_name, route_id_field_type,
                                  field_length=route_id_field_length)
        arcpy.management.AddField(out_table, 'FromMeasure', "DOUBLE")
        arcpy.management.AddField(out_table, 'ToMeasure', "DOUBLE")

        # Populate event table using cursors
        search_fields = [route_id_field_name, "SHAPE@"]
        update_fields = [route_id_field_name, "FromMeasure", "ToMeasure"]
        with arcpy.da.InsertCursor(out_table, update_fields) as icursor:
            with arcpy.da.SearchCursor(in_routes, search_fields) as cursor:
                for row in cursor:
                    line = row[1]
                    first_measure = float(line.firstPoint.M)
                    last_measure = float(line.lastPoint.M)
                    icursor.insertRow((row[0], first_measure, last_measure))
        return
