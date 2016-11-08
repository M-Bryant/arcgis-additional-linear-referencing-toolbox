"""
StationPointsAndCrossSections.py

Generates station points at equal interval along a line,
and creates cross sections of a specified width at the station point
from an input polyline feature class.

Usage:      generateStationPointsAndCrossSections
                                    <inputPolylineFeatureLayer>
                                    <routeIdField>
                                    <stationFieldName>
                                    <stationSeparation>
                                    <outputRoutePolylineFC>
                                    <outputRoutePointFC>
                                    <crossSectionWidth>
                                    <crossSectionNameField>
                                    <outputCrossSectionFC>
    Where:

    <inputPolylineFeatureLayer> is the input polyline feature class that
    will be processed to create the output route features.
    The input polyline feature class need not have M values; these will be
    calculated using line length.

    <routeIdField> is a string field in the input polyline feature class
    that stores line names. Line names must be unique within the input
    polyline feature class.

    <stationFieldName> is the name of a text field that will be added to
    the route feature class to identify the station sequence.
    The station values will used to help build unique cross sections.

    <stationSeparation> is the name of a double field that will be used to
    specify the horizontal distance between each point, or station, along
    the input polyline feature class.

    <outputRoutePolylineFC> is the name of a PolylineM feature class that
    will be created from the input polyline features. Measures
    will be assigned in the direction of line digitization starting with
    the begin measure and ending with the end measure value.

    <outputRoutePointFC> is the name of a PointM feature class that
    will be created and will store the output station series.

    <crossSectionWidth> is used to specify how wide the cross section
    drawn through the station point will be. Note that with distance from
    the route line will be half of the section width.

    <crossSectionNameField> is the name of a text field  target that will
    be added to the cross section. The field will be populated with
    <routeIdField> _ <stationFieldName>

    <outputCrossSectionFC> is the target ControlPoint feature class that
    will be created to hold the final cross section. Cross Sections will
    be drawm from left to right, based on direction of line digitization.

------------------------------------------------------------------------------
Author:           mark.bryant@aecom.com
Created:          04/04/2013
Copyright:        (c) AECOM
ArcGIS Version:   10
Python Version:   2.6
------------------------------------------------------------------------------
"""

# Set the necessary modules
import os
import math
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


def create_cross_section(station_feature_class, route_id_field_name, cross_section_width, out_cross_section_feature_class):
    """
    station_feature_class, point
    route_id, measure, loc_angle
    """
    # Create the output table
    path, name = os.path.split(out_cross_section_feature_class)
    arcpy.management.CreateFeatureclass(path, name, "POLYLINE", spatial_reference=station_feature_class)

    # get infomation about the route_id field
    route_id_field = get_field(station_feature_class, route_id_field_name)
    route_id_field_type = route_id_field.type
    route_id_field_length = route_id_field.length

    # Add Fields
    arcpy.management.AddField(out_cross_section_feature_class, route_id_field_name, route_id_field_type,
                                field_length=route_id_field_length)
    arcpy.management.AddField(out_cross_section_feature_class, 'Measure', "DOUBLE")

    distance = cross_section_width/2.0

    search_fields = ["SHAPE@XY", route_id_field_name, 'Measure', 'LOC_ANGLE']
    insert_fields = ["SHAPE@", route_id_field_name, 'Measure'] 
    sql_clause=(None, 'ORDER BY {}, Measure'.format(route_id_field_name))
    with arcpy.da.InsertCursor(out_cross_section_feature_class, insert_fields) as icursor:
        with arcpy.da.SearchCursor(station_feature_class, search_fields, sql_clause=sql_clause) as cursor:
            for row in cursor:
                mid_x, mid_y = row[0]
                bearing = math.radians(row[3])

                from_x = mid_x + distance * math.cos(bearing)
                from_y = mid_y + distance * math.sin(bearing)
                to_x = mid_x - distance * math.cos(bearing)
                to_y = mid_y - distance * math.sin(bearing)

                from_point = arcpy.Point(from_x, from_y)
                to_point = arcpy.Point(to_x, to_y)
                mid_point = arcpy.Point(mid_x, mid_y)
                # Create three point line
                array = arcpy.Array([from_point, mid_point, to_point])
                polyline = arcpy.Polyline(array)
                icursor.insertRow([polyline, row[1], row[2]])


class StationPointsAndCrossSections(object):
    """Generate Station Points And Cross-Sections"""
    def __init__(self):
        self.label = 'Station Points And Cross-Sections'
        self.description = ('Generates station points at equal interval along a line, '
                            'then creates cross-sections of a specified width '
                            'from an input polyline feature class.')
        self.category = 'Hydrology'
        self.canRunInBackground = True

    def getParameterInfo(self):
        # Input_Line_Features
        in_line_features = arcpy.Parameter(
            displayName='Input Line Features',
            name='in_line_features',
            datatype='GPFeatureLayer',
            parameterType='Required',
            direction='Input')
        in_line_features.filter.list = ["Polyline"]

        # Route_Identifier_Field
        route_id_field = arcpy.Parameter(
            displayName='Route Identifier Field',
            name='route_id_field',
            datatype='Field',
            parameterType='Required',
            direction='Input')
        route_id_field.filter.list = ['Short', 'Long', 'Text']
        route_id_field.parameterDependencies = [in_line_features.name]

        # Station_Separation
        station_interval = arcpy.Parameter(
            displayName='Station separation',
            name='station_interval',
            datatype='GPDouble',
            parameterType='Required',
            direction='Input')
        station_interval.value = 10.0

        # Cross_Section_Width
        cross_section_width = arcpy.Parameter(
            displayName='Cross Section Width',
            name='cross_section_width',
            datatype='GPDouble',
            parameterType='Required',
            direction='Input')
        cross_section_width.value = 100.0

        # Output_Route_Feature_Class
        out_route_feature_class = arcpy.Parameter(
            displayName='Output Route Feature Class',
            name='out_route_feature_class',
            datatype='DEFeatureClass',
            parameterType='Required',
            direction='Output')

        # Output_Station_Point_Feature_Class
        out_station_feature_class = arcpy.Parameter(
            displayName='Output Station Point Feature Class',
            name='out_station_feature_class',
            datatype='DEFeatureClass',
            parameterType='Required',
            direction='Output')

        # Output_Cross_Section_Feature_Class
        out_cross_section_feature_class = arcpy.Parameter(
            displayName='Output Cross Section Feature Class',
            name='out_cross_section_feature_class',
            datatype='DEFeatureClass',
            parameterType='Required',
            direction='Output')

        params = [in_line_features, route_id_field,
                  station_interval, cross_section_width, 
                  out_route_feature_class, out_station_feature_class,
                  out_cross_section_feature_class]
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
            if not parameters[4].altered:
                parameters[4].value = os.path.join(path, 'out_route')
            if not parameters[5].altered:
                parameters[5].value = os.path.join(path, 'out_points')
            if not parameters[6].altered:
                parameters[6].value = os.path.join(path, 'out_xsection')
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        in_line_features = parameters[0].valueAsText
        route_id_field = parameters[1].valueAsText
        station_interval = parameters[2].value
        cross_section_width = parameters[3].value
        out_route_feature_class = parameters[4].valueAsText
        out_station_feature_class = parameters[5].valueAsText
        out_cross_section_feature_class = parameters[6].valueAsText

        arcpy.env.overwriteOutput = True

        # Create route from polyline by length
        create_route_by_length(in_features=in_line_features,route_id_field=route_id_field,route_feature_class=out_route_feature_class)
        # Create a unique in_memory name
        event_tbl = arcpy.CreateUniqueName('event_table', 'in_memory')
        
        create_point_event_table(out_route_feature_class, route_id_field_name=route_id_field, measure_interval=station_interval, out_table=event_tbl)

        # locate points along route
        event_properties = '{} {} {}'.format(route_id_field, "POINT", 'Measure')
        arcpy.lr.MakeRouteEventLayer(in_routes=out_route_feature_class,
                                     route_id_field=route_id_field,
                                     in_table=event_tbl, in_event_properties=event_properties,
                                     out_layer='Point Events',
                                     add_angle_field=True, angle_type="NORMAL",
                                     point_event_type="POINT")


        # Save points to feature class
        arcpy.management.CopyFeatures('Point Events', out_station_feature_class)
        #Create x section
        create_cross_section(out_station_feature_class, route_id_field, cross_section_width, out_cross_section_feature_class)
        
        return
     