import pandera.pandas as pa
from pandera.pandas import Column, DataFrameSchema

# --- Pandera Schemas ---
# Validating the expected loose structure of the raw datasets. 
# We use coerce=True to handle slight type variations where possible, and required=False 
# for columns that are conditionally extracted via df.get() in the logic.

# Unified Schema for the final output
unified_schema = DataFrameSchema({
    "source_file_name": Column(pa.String, nullable=False, required=True),
    "source_identifier": Column(pa.String, nullable=False, required=True),
    "region": Column(pa.String, nullable=False, required=True),
    "original_crime_type": Column(pa.String, nullable=False, required=True),
    "mapped_crime_category": Column(pa.String, nullable=False, required=True),
    "occurrence_date": Column(pa.String, nullable=True),
    "lat": Column(pa.Float, nullable=False, required=True),
    "lon": Column(pa.Float, nullable=False, required=True),
    "municipality": Column(pa.String, nullable=False, required=True),
}, coerce=True)


# Raw Data Schemas

durham_schema = DataFrameSchema({
    "event_unique_id": Column(pa.String, nullable=True, required=False, coerce=True),
    "report_year": Column(pa.Int, nullable=True, required=False, coerce=True),
    "report_month": Column(pa.String, nullable=True, required=False, coerce=True),
    "report_day": Column(pa.Int, nullable=True, required=False, coerce=True),
    "report_hour": Column(pa.Int, nullable=True, required=False, coerce=True),
    "report_dow": Column(pa.String, nullable=True, required=False, coerce=True),
    "occurrence_year": Column(pa.Int, nullable=True, required=False, coerce=True),
    "occurrence_month": Column(pa.String, nullable=True, required=False, coerce=True),
    "occurrence_day": Column(pa.Int, nullable=True, required=False, coerce=True),
    "occurrence_hour": Column(pa.Int, nullable=True, required=False, coerce=True),
    "occurrence_dow": Column(pa.String, nullable=True, required=False, coerce=True),
    "municipality": Column(pa.String, nullable=True, required=False, coerce=True),
    "division": Column(pa.String, nullable=True, required=False, coerce=True),
    "lat": Column(pa.Float, nullable=True, required=False, coerce=True),
    "lon": Column(pa.Float, nullable=True, required=False, coerce=True),
    "offence": Column(pa.String, nullable=True, required=False, coerce=True),
    "neighbourhood": Column(pa.String, nullable=True, required=False, coerce=True),
    "location_type": Column(pa.String, nullable=True, required=False, coerce=True),
    "ObjectId": Column(pa.Int, nullable=True, required=False, coerce=True),
    "x": Column(pa.Float, nullable=True, required=False, coerce=True),
    "y": Column(pa.Float, nullable=True, required=False, coerce=True),
}, coerce=True)

halton_schema = DataFrameSchema({
    "OBJECTID": Column(pa.Int, nullable=True, required=False, coerce=True),
    "CASE_NO": Column(pa.String, nullable=True, required=False, coerce=True),
    "DATE": Column(pa.Int, nullable=True, required=False, coerce=True),
    "DESCRIPTION": Column(pa.String, nullable=True, required=False, coerce=True),
    "LOCATION": Column(pa.String, nullable=True, required=False, coerce=True),
    "CITY": Column(pa.String, nullable=True, required=False, coerce=True),
    "Latitude": Column(pa.Float, nullable=True, required=False, coerce=True),
    "Longitude": Column(pa.Float, nullable=True, required=False, coerce=True),
    "GlobalID": Column(pa.String, nullable=True, required=False, coerce=True),
    "lat": Column(pa.Float, nullable=True, required=False, coerce=True),
    "lon": Column(pa.Float, nullable=True, required=False, coerce=True),
}, coerce=True)

peel_schema = DataFrameSchema({
    "OBJECTID": Column(pa.Int, nullable=True, required=False, coerce=True),
    "OccurrenceNumber": Column(pa.String, nullable=True, required=False, coerce=True),
    "OccurrenceDate": Column(pa.String, nullable=True, required=False, coerce=True),
    "OccurrenceTime": Column(pa.String, nullable=True, required=False, coerce=True),
    "OccDate": Column(pa.Int, nullable=True, required=False, coerce=True),
    "OccDateUTC": Column(pa.Int, nullable=True, required=False, coerce=True),
    "OccurrenceWeekday": Column(pa.String, nullable=True, required=False, coerce=True),
    "OccurrenceHour": Column(pa.Int, nullable=True, required=False, coerce=True),
    "OccMonth": Column(pa.String, nullable=True, required=False, coerce=True),
    "OccYear": Column(pa.Int, nullable=True, required=False, coerce=True),
    "Description": Column(pa.String, nullable=True, required=False, coerce=True),
    "ClearanceStatus": Column(pa.String, nullable=True, required=False, coerce=True),
    "StreetName": Column(pa.String, nullable=True, required=False, coerce=True),
    "StreetType": Column(pa.String, nullable=True, required=False, coerce=True),
    "Municipality": Column(pa.String, nullable=True, required=False, coerce=True),
    "PatrolZone": Column(pa.String, nullable=True, required=False, coerce=True),
    "Division": Column(pa.String, nullable=True, required=False, coerce=True),
    "OccType": Column(pa.String, nullable=True, required=False, coerce=True),
    "Ward": Column(pa.String, nullable=True, required=False, coerce=True),
    "lat": Column(pa.Float, nullable=True, required=False, coerce=True),
    "lon": Column(pa.Float, nullable=True, required=False, coerce=True),
}, coerce=True)

toronto_schema = DataFrameSchema({
    "OBJECTID": Column(pa.Int, nullable=True, required=False, coerce=True),
    "EVENT_UNIQUE_ID": Column(pa.String, nullable=True, required=False, coerce=True),
    "REPORT_DATE": Column(pa.String, nullable=True, required=False, coerce=True),
    "OCC_DATE": Column(pa.String, nullable=True, required=False, coerce=True),
    "REPORT_YEAR": Column(pa.Int, nullable=True, required=False, coerce=True),
    "REPORT_MONTH": Column(pa.String, nullable=True, required=False, coerce=True),
    "REPORT_DAY": Column(pa.Int, nullable=True, required=False, coerce=True),
    "REPORT_DOY": Column(pa.Int, nullable=True, required=False, coerce=True),
    "REPORT_DOW": Column(pa.String, nullable=True, required=False, coerce=True),
    "REPORT_HOUR": Column(pa.Int, nullable=True, required=False, coerce=True),
    "OCC_YEAR": Column(pa.Float, nullable=True, required=False, coerce=True),
    "OCC_MONTH": Column(pa.String, nullable=True, required=False, coerce=True),
    "OCC_DAY": Column(pa.Float, nullable=True, required=False, coerce=True),
    "OCC_DOY": Column(pa.Float, nullable=True, required=False, coerce=True),
    "OCC_DOW": Column(pa.String, nullable=True, required=False, coerce=True),
    "OCC_HOUR": Column(pa.Int, nullable=True, required=False, coerce=True),
    "DIVISION": Column(pa.String, nullable=True, required=False, coerce=True),
    "LOCATION_TYPE": Column(pa.String, nullable=True, required=False, coerce=True),
    "PREMISES_TYPE": Column(pa.String, nullable=True, required=False, coerce=True),
    "UCR_CODE": Column(pa.Int, nullable=True, required=False, coerce=True),
    "UCR_EXT": Column(pa.Int, nullable=True, required=False, coerce=True),
    "OFFENCE": Column(pa.String, nullable=True, required=False, coerce=True),
    "CSI_CATEGORY": Column(pa.String, nullable=True, required=False, coerce=True),
    "HOOD_158": Column(pa.String, nullable=True, required=False, coerce=True),
    "NEIGHBOURHOOD_158": Column(pa.String, nullable=True, required=False, coerce=True),
    "HOOD_140": Column(pa.String, nullable=True, required=False, coerce=True),
    "NEIGHBOURHOOD_140": Column(pa.String, nullable=True, required=False, coerce=True),
    "LONG_WGS84": Column(pa.Float, nullable=True, required=False, coerce=True),
    "LAT_WGS84": Column(pa.Float, nullable=True, required=False, coerce=True),
    "x": Column(pa.Float, nullable=True, required=False, coerce=True),
    "y": Column(pa.Float, nullable=True, required=False, coerce=True),
}, coerce=True)

york_schema = DataFrameSchema({
    "UniqueIdentifier": Column(pa.String, nullable=True, required=False, coerce=True),
    "Occurrence Detail": Column(pa.String, nullable=True, required=False, coerce=True),
    "Location Code": Column(pa.String, nullable=True, required=False, coerce=True),
    "District": Column(pa.String, nullable=True, required=False, coerce=True),
    "Municipality": Column(pa.String, nullable=True, required=False, coerce=True),
    "Special Grouping": Column(pa.String, nullable=True, required=False, coerce=True),
    "OBJECTID": Column(pa.Float, nullable=True, required=False, coerce=True),
    "Shooting": Column(pa.String, nullable=True, required=False, coerce=True),
    "Hate Crime": Column(pa.String, nullable=True, required=False, coerce=True),
    "Status": Column(pa.String, nullable=True, required=False, coerce=True),
    "Occurrence Type": Column(pa.String, nullable=True, required=False, coerce=True),
    "Report Date": Column(pa.String, nullable=True, required=False, coerce=True),
    "Time": Column(pa.String, nullable=True, required=False, coerce=True),
    "Occurrence Date": Column(pa.String, nullable=True, required=False, coerce=True),
    "x": Column(pa.Float, nullable=True, required=False, coerce=True),
    "y": Column(pa.Float, nullable=True, required=False, coerce=True),
}, coerce=True)
