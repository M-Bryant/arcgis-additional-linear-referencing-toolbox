"""
create_route_by_length.py
Converts features into measured routes based on the length of the lines.
The input line features that share a common identifier are merged to create
a single route.
Process should only be run on simple lines (no multi-part).
If merging on common id, geometry direction should also align.

Wrapper around the Linear Referencing Create Routes tool
using the TWO_FIELDS Measure Source option
"""
import arcpy


def create_route_by_length(in_features, route_id_field, route_feature_class):
    """Converts features into measured routes based on the length of the lines.
    The input line features that share a common identifier are merged to create
    a single route.
    Process should only be run on simple lines (no multi-part).
    If merging on common id, geometry direction should also align.
    """
    # Create a unique in_memory name
    the_line = arcpy.CreateUniqueName('theLine', 'in_memory')
    # Copy to memory as to not alter original and speed
    arcpy.management.CopyFeatures(in_features, the_line)
    # Add Fields
    arcpy.management.AddField(the_line, 'FromMeasure', "DOUBLE",
                              field_is_nullable='NULLABLE',
                              field_is_required='NON_REQUIRED')
    arcpy.management.AddField(the_line, 'ToMeasure', "DOUBLE",
                              field_is_nullable='NULLABLE',
                              field_is_required='NON_REQUIRED')
    # Update the in_memory table
    update_fields = ['FromMeasure', 'ToMeasure', 'SHAPE@LENGTH']
    with arcpy.da.UpdateCursor(the_line, update_fields) as cursor:
        for row in cursor:
            row[0] = 0
            row[1] = row[2]
            cursor.updateRow(row)

    # Create Route
    arcpy.lr.CreateRoutes(the_line, route_id_field, route_feature_class,
                          measure_source='TWO_FIELDS',
                          from_measure_field='FromMeasure',
                          to_measure_field='ToMeasure')

    # Delete the in_memory line
    arcpy.management.Delete(the_line)
    # Return the route
    return route_feature_class


class CreateRouteByLength(object):
    """Converts features into measured routes based on the length of the lines"""
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = 'Create Route by Length'
        self.description = 'Create measured routes based on the length of the lines.'
        self.category = 'Linear Referencing'
        self.canRunInBackground = True

    def getParameterInfo(self):
        """Define parameter definitions"""
        in_line_features = arcpy.Parameter(
            displayName='Input Line Features',
            name='in_line_features',
            datatype='GPFeatureLayer',
            parameterType='Required',
            direction='Input')
        in_line_features.filter.list = ["Polyline"]

        route_id_field = arcpy.Parameter(
            displayName='Route Identifier Field',
            name='route_id_field',
            datatype='Field',
            parameterType='Required',
            direction='Input')

        route_id_field.filter.list = ['Short', 'Long', 'Text']
        route_id_field.parameterDependencies = [in_line_features.name]

        out_feature_class = arcpy.Parameter(
            displayName='Output Route Feature Class',
            name='out_feature_class',
            datatype='DEFeatureClass',
            parameterType='Required',
            direction='Output')

        params = [in_line_features, route_id_field, out_feature_class]
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
        in_line_features = parameters[0].valueAsText
        route_id_field = parameters[1].valueAsText
        out_feature_class = parameters[2].valueAsText

        create_route_by_length(in_line_features, route_id_field, out_feature_class)
        return
