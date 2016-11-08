"""
createPointsAlongLine.py

Generates station points at equal interval along a line,
from an input polyline feature class.
Uses Linear Referencing

mark.bryant@aecom.com
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




class PointsAlongLine(object):
    """Generate points along lines using linear referencing"""
    def __init__(self):
        self.label = 'Points Along Line'
        self.description = ('Generates station points at equal interval along a line, '
                            'from an input polyline feature class.')
        self.category = 'Linear Referencing'
        self.canRunInBackground = True

    def getParameterInfo(self):
        """Define parameter definitions"""
        # Input_Line_Features
        in_line_features = arcpy.Parameter(
            displayName='Input Line Features',
            name='in_features',
            datatype='GPFeatureLayer',
            parameterType='Required',
            direction='Input')
        in_line_features.filter.list = ["Polyline"]

        # Route_Identifier_Field
        route_id_field = arcpy.Parameter(
            displayName='Route Identifier Field',
            name='route_id',
            datatype='Field',
            parameterType='Required',
            direction='Input')
        route_id_field.filter.list = ['Short', 'Long', 'Text']
        route_id_field.parameterDependencies = [in_line_features.name]

        # Station_Separation
        measure_interval = arcpy.Parameter(
            displayName='Station separation',
            name='measure_interval',
            datatype='GPDouble',
            parameterType='Required',
            direction='Input')
        measure_interval.value = 100.0

        # Output_Point_Feature_Class
        out_point_feature_class = arcpy.Parameter(
            displayName='Output Point Feature Class',
            name='out_point_feature_class',
            datatype='DEFeatureClass',
            parameterType='Required',
            direction='Output')

        # Output_Route_Feature_Class
        out_route_feature_class = arcpy.Parameter(
            displayName='Output Route Feature Class',
            name='out_route_feature_class',
            datatype='DEFeatureClass',
            parameterType='Required',
            direction='Output')

        params = [in_line_features, route_id_field,
                  measure_interval, out_point_feature_class,
                  out_route_feature_class]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        if parameters[0].value:
            # Create inital output featureclasses
            layer = parameters[0].value
            desc = arcpy.Describe(layer)
            if hasattr(desc, "catalogPath"):
                path, dummy = os.path.split(desc.catalogPath)
            else:
                path = arcpy.env.scratchGDB
            if not parameters[3].altered:
                parameters[3].value = os.path.join(path, 'out_points')
            if not parameters[4].altered:
                parameters[4].value = os.path.join(path, 'out_route')

        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        in_line_features = parameters[0].valueAsText
        route_id_field = parameters[1].valueAsText
        measure_interval = parameters[2].value
        out_point_feature_class = parameters[3].valueAsText
        out_route_feature_class = parameters[4].valueAsText

        arcpy.env.overwriteOutput = True

        # Create route from polyline by length
        create_route_by_length(in_features=in_line_features, route_id_field=route_id_field,
                               route_feature_class=out_route_feature_class)

        # Create a set of UniqueNames for in_memory features
        event_tbl = arcpy.CreateUniqueName('event_table', 'in_memory')
        #point_fc = arcpy.CreateUniqueName('point_fc', 'in_memory')

        # Create point event table
        create_point_event_table(out_route_feature_class, route_id_field_name=route_id_field,
                                 measure_interval=measure_interval, out_table=event_tbl)
        # locate points along route
        event_properties = '{} {} {}'.format(route_id_field, "POINT", 'Measure')
        arcpy.lr.MakeRouteEventLayer(in_routes=out_route_feature_class,
                                     route_id_field=route_id_field,
                                     in_table=event_tbl, in_event_properties=event_properties,
                                     out_layer='Point Events',
                                     add_angle_field=True, angle_type="NORMAL",
                                     point_event_type="POINT")
        # Save points to feature class
        arcpy.management.CopyFeatures('Point Events', out_point_feature_class)

        # Cleanup
        if arcpy.Exists(event_tbl):
            arcpy.management.Delete(event_tbl)
        if arcpy.Exists('Point Events'):
            arcpy.management.Delete('Point Events')
        return
