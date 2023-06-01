import numpy as np
import pandas as pd
import os
import re

def prettify_loadsheet(loadsheet_path):
        try:
            valid_file_types = {
                '.xlsx': 'excel',
                '.csv': 'bms_file'
            }
            file_type = os.path.splitext(loadsheet_path)[1]

            assert file_type in valid_file_types, f"Path '{loadsheet_path}' is not a valid file type (only .xlsx and .csv allowed)."
            assert os.path.exists(
                loadsheet_path), f"Loadsheet path '{loadsheet_path}' is not valid."
            try:
                building_name = str(
                    input("Please enter building name (site code): "))

                colname_map = {
                    'Location': 'location',
                    'generaltype': 'generalType',
                    'globalphredentitycode': 'fullAssetPath',
                    'standardfieldname': 'standardFieldName',
                    'phredentitycode': 'assetName'
                }

                if file_type == '.xlsx':
                    df = pd.read_excel(loadsheet_path)
                elif file_type == '.csv':
                    df = pd.read_csv(loadsheet_path)
                else:
                    print(
                        f'Something went wrong with importing your {file_type}')
                    return

                # standardizing column names
                colname_map = {
                    'Location': 'location',
                    'Control Program': 'controlProgram',
                    'Name': 'name',
                    'Type': 'type',
                    'Device ID': 'deviceId',
                    'Object Name': 'objectName',
                    'Path': 'path'
                }
                df.rename(columns=colname_map, inplace=True)

                df.drop(['I/O Type'], axis='columns', inplace=True)
                df = df[df['Object ID'].str.contains(":")]
                df['objectType'] = df['Object ID'].apply(
                    lambda x: x.split(':')[0])
                df['objectId'] = df['Object ID'].apply(
                    lambda x: x.split(':')[1])

                # adding new columns
                df['building'] = building_name
                df['manuallyMapped'] = np.nan
                df['generalType'] = np.nan
                df['units'] = np.nan
                df['required'] = np.nan
                df['typeName'] = np.nan
                df['assetName'] = np.nan
                df['fullAssetPath'] = np.nan
                df['standardFieldName'] = np.nan

                # reordering columns
                df = df[['location', 'controlProgram', 'name', 'type', 'path', 'deviceId', 'objectType', 'objectId',
                        'objectName', 'units', 'required', 'manuallyMapped', 'building', 'generalType', 'typeName',
                        'assetName', 'fullAssetPath', 'standardFieldName']]
                export_path = re.sub('(.xlsx)?(.csv)?', '', loadsheet_path)
                df.to_excel(f'{export_path}_pretty.xlsx', index=False)

            except Exception as e:
                print("[ERROR]\tLoadsheet raised errors: {}".format(e))

        except Exception as e:
            print("[ERROR]\tCould not load: {}".format(e))
