#Copyright 2020 DB Engineering

#Licensed under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License.
#You may obtain a copy of the License at

#    http://www.apache.org/licenses/LICENSE-2.0

#Unless required by applicable law or agreed to in writing, software
#distributed under the License is distributed on an "AS IS" BASIS,
#WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#See the License for the specific language governing permissions and
#limitations under the License.

__version__ = '0.0.3'
__author__ = 'Trevor S., Shane S., Andrew K.'

# Standard Packages
import os
import sys
import string
import win32com.client as win32
from datetime import datetime

from typing import Optional
from typing import Union
from typing import Dict
from typing import List
from typing import Any

# Open-source Packages
import openpyxl
import re
import pandas as pd

sys.path.append('../')

# Proprietary Packages
from rules.rules import Rules

# Module GOBAL and CONTRAINTS

# 01132021: bms specific
_REQ_INPUT_HEADERS_BMS = [
        'location', 
        'controlprogram', 
        'name', 
        'type', 
        'objectid', 
        'deviceid', 
        'objectname', 
        'path'
        ]

# 01132021: general
_REQ_INPUT_HEADERS = _REQ_INPUT_HEADERS_BMS + ['units', 'objecttype']

_REQ_OUTPUT_HEADERS = [
        'required',
        'manuallymapped',
        'building',
        'generaltype',
        'typename',
        'assetname',
        'fullassetpath',
        'standardfieldname',
        'ismissing'
        ]

_REQ_OUTPUT_HEADERS_ORIG = [
        'required',
        'manuallyMapped',
        'building',
        'generalType',
        'typeName',
        'assetName',
        'fullAssetPath',
        'standardFieldName',
        'isMissing'
        ]

_ML_PREDICTION_HEADERS = ['required',
                        'units',
                        'assetName',
                        'objectType',
                        'required_conf',
                        'standardFieldName',
                        'standardFieldName_conf',
                        'standardFieldName_alt',
                        'generalType']


_STD_ORDERED_HEADERS = [
        'location', 
        'controlprogram', 
        'name', 
        'type', 
        'deviceid', 
        'objecttype',
        'objectid', 
        'objectname', 
        'path',
        'required',
        'units',
        'manuallymapped',
        'ismissing',
        'building',
        'generaltype',
        'typename',
        'assetname',
        'fullassetpath',
        'standardfieldname',
        'requiredconf',
        'standardfieldnameconf',
        'standardfieldnamealt',
]


class Loadsheet:
    """
    Loadsheet Library

    Purpose:		The Loadsheet Library (loadsheet.py) is a proprietary class
                            used to load a loadsheet Excel file into the tool

    Args: data - the list of dictionaries making up the loadsheet file
                 Keys are column names, values are column values

    Returns: Loadsheet object

    Usage Example(s):

            1) From records:
               data = {'coln1':[1,2,3], 'coln2':['a','b','c']}
               ls = Loadsheet(data)

            2) From loadsheet excel file*:
               ls = Loadsheet.from_loadsheet(<loadsheet_file_path>)

            3) From BMS file*:
               ls = Loadsheet.from_bms(<bms_file_path>)

            * - By default, expects header row at top

    Dependencies:

            Standard
            - os
            - sys

            Open-source
            - openpyxl
            - yaml
            - typing

            Proprietary
            - rules

    TODOs:
        - ini_config not used but will be added in future
        - all rows will have same headers, so add header check
    """

    def __init__(
            self,
            data: List[Dict[str,Any]],
            std_header_map: Dict[str,str],

            #has_normalized_fields: bool= False,
            ):

        # 01132021: moved this check to import format specific method(s)
        #		currently a quick fix for a much broader update refactor
        #		that needs to be done
        # assert Loadsheet._is_valid_headers(data[0].keys(), has_normalized_fields) == True,\
        # 		"[ERROR] loadsheet headers:\n {} \ndo not match configuration \
        # 		headers:\n {}".format(', '.join(data[0].keys()),', '.join(
        # 			*[_REQ_INPUT_HEADERS+_REQ_OUTPUT_HEADERS if has_normalized_fields
        # 			else _REQ_INPUT_HEADERS]))
        # # end by sypks
        new_data = []
        # converts camel case keys to lowercase, all fields are referenced as lowercase further (added 2023-06-01)
        for row in data:
            new_data.append({k.lower(): v for k, v in row.items()})
        self._data = new_data
        self._std_header_map = std_header_map

    def _update_header_map(self, orig_headers: List[str]):
        """
        Updates the header map for the loadsheet object
        args:
            header_map - dictionary mapping of new headers to old headers
        returns:
            None
        """
        std_headers = Loadsheet._to_std_headers(orig_headers)
        for orig, std in zip(orig_headers, std_headers):
            if std not in self._std_header_map.keys():
                self._std_header_map[std] = orig

    def _update_data_from_dataframe(self, df):
        """
        Updates the data in the loadsheet object from a dataframe
        args:
            df - dataframe to update the data in the loadsheet object
        returns:
            None
        """
        self._data = df.to_dict('records')

    @staticmethod
    def _parse_building_name(text: str) -> str:
        """
        Parses the building name from the input string
        args:
            input - input string to parse the building name from
        returns:
            building name as a string
        """
        if text is None:
            return ''
        
        text = text.replace("_", "-")
        
        COUNTRY_ID_PATTERN = '[A-Za-z]{2}'
        CITY_ID_PATTERN = '[A-Za-z]{2,4}'
        BUILDING_ID_PATTERN = '[A-Za-z0-9]{2,10}'
        BUILDING_CODE_PATTERN = f'({COUNTRY_ID_PATTERN})-({CITY_ID_PATTERN})-({BUILDING_ID_PATTERN})'
        BUILDING_CODE_REGEX = re.compile(BUILDING_CODE_PATTERN)

        match = re.search(BUILDING_CODE_REGEX, text)
        if match:
            return match.group(0).strip().upper()
        else:
            code = input("Could not parse building code from input, please enter building code in the format: <country>-<city>-<building>:")
            return code.strip().upper()

    @staticmethod
    def _order_data(df: pd.DataFrame) -> pd.DataFrame:
        """
        Orders the data in the dataframe based on the order of the headers
        args:
            df - dataframe to order
        returns:
            dataframe with ordered data
        """

        ordered_data_headers = [h for h in _STD_ORDERED_HEADERS if h in df.columns]
        return df[ordered_data_headers]

    def create_pivot_table(self, path: str) -> None:
        # Create pivot table using win32com (native Excel)
        excel = win32.gencache.EnsureDispatch('Excel.Application')
        excel.Visible = False  # Set True for debugging
        wb = excel.Workbooks.Open(path)
        ws_data = wb.Sheets("Sheet1")
        sheet_names = [sheet.Name for sheet in wb.Sheets]

        # Get the used range dynamically
        last_row = ws_data.UsedRange.Rows.Count
        last_col = ws_data.UsedRange.Columns.Count
        col_letter = chr(64 + last_col)  # assumes < 26 columns

        # Build source range like "Sheet1!A1:D100"
        source_range = f"Sheet1!A1:{col_letter}{last_row}"

        # Create pivot cache
        pivot_cache = wb.PivotCaches().Create(
            SourceType=1,  # xlDatabase
            SourceData=source_range
        )

        # Add Pivot sheet
        if "Pivot" in sheet_names:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
            sheet_name = f"Pivot_{timestamp}"
        else: sheet_name = "Pivot"
        try:
            ws_pivot = wb.Sheets("Pivot")
        except:
            ws_pivot = wb.Sheets.Add(After=wb.Sheets(wb.Sheets.Count))
            ws_pivot.Name = sheet_name

        # Create pivot table at top left
        pivot_table = pivot_cache.CreatePivotTable(
            TableDestination=f"Pivot!R1C1",
            TableName="AssetPivot"
        )

        # Set pivot fields
        pf = pivot_table.PivotFields

        # Set assetName as row field
        pf("assetName").Orientation = 1  # xlRowField
        pf("standardFieldName").Orientation = 2  # xlColumnField
        pf("standardFieldName").Orientation = 4  # xlDataField

        # Add filters
        pf("required").Orientation = 3  # xlPageField
        pf("generalType").Orientation = 3  # xlPageField

        # Make column labels (standardFieldName) vertical
        pivot_table.PivotFields("standardFieldName").DataRange.Cells.HorizontalAlignment = -4131  # xlCenter
        pivot_table.PivotFields("standardFieldName").DataRange.Cells.VerticalAlignment = -4130  # xlCenter
        pivot_table.PivotFields("standardFieldName").DataRange.Cells.Orientation = 90  # Rotate text 90 degrees (vertical)

        # Save and close
        wb.Save()
        wb.Close()
        excel.Quit()

    @classmethod
    def from_loadsheet(
            cls,
            filepath: str,
            has_normalized_fields: bool= False
            ):
        """
        Initializes loadsheet object from existing loadsheet Excel file
        args:
            filepath - absolute filepath to loadsheet excel file
            has_normalized_fields - flag if has normalized fields
        returns:
            loadsheet object
        """
        # hardcode header rows as [0] for initial release
        valid_file_types = {
            '.xlsx':'excel',
            '.csv':'bms_file'
        }
        file_type = os.path.splitext(filepath)[1]


        if file_type == '.xlsx':
            df = pd.read_excel(filepath, header= 0)
        elif file_type == '.csv':
            df = pd.read_csv(filepath, header= 0)
        std_header_map = Loadsheet._to_std_header_mapping(
                df.columns)
        df.columns = std_header_map.keys()

        # 01132021: check to ensure that document has required headers
        if not Loadsheet._is_valid_headers(
                df.columns,
                _REQ_INPUT_HEADERS,
                has_normalized_fields
                ):
            header_list = [header.lower() for header in df.columns.tolist()]
            raise RuntimeError("[ERROR] Loadsheet headers:\n {} \nDoes not match "
                + "configuration headers:\n {}".format(', '.join(header_list),', '.join(
                 *[_REQ_INPUT_HEADERS+_REQ_OUTPUT_HEADERS if has_normalized_fields
                 else _REQ_INPUT_HEADERS])))

        return cls(
            df.to_dict('records'),
            std_header_map
            )
        # end by sypks

    @classmethod
    def from_bms(
            cls,
            filepath: str
            ):
        """
        Initializes loadsheet object from existing BMS file
        args:
            filepath - absolute filepath to BMS file
            ini_config_filepath - not currently enabled, do not use
        returns:
            loadsheet object
        """

        file_type = os.path.splitext(filepath)[1]

        if file_type == '.xlsx':
            df = pd.read_excel(filepath, header= 0, engine="openpyxl")
        elif file_type == '.csv':
            df = pd.read_csv(filepath, header= 0, encoding="utf-8")

        df.drop(['I/O Type'], axis='columns', inplace=True)
        df = df.dropna(subset=['Object ID'], axis=0)
        df = df[df['Object ID'].str.contains(":")]
        df['objectType'] = ''
        df.rename(columns={
                        'Location': 'location',
                        'Control Program': 'controlProgram',
                        'Name': 'name',
                        'Type': 'type',
                        'Device ID': 'deviceId',
                        'Object ID': 'objectId',
                        'Path': 'path',
                        'Object Name': 'objectName',
                        'Path': 'path'}, inplace=True)
        df['building'] = Loadsheet._parse_building_name(filepath)

        std_header_map = Loadsheet._to_std_header_mapping(
                df.columns)

        df.columns = std_header_map.keys()
        
        for orig, std in zip(_REQ_OUTPUT_HEADERS_ORIG, _REQ_OUTPUT_HEADERS):
            if std not in std_header_map.keys():
                std_header_map[std] = orig

        # 01132021: check to ensure that document has required headers
        if not Loadsheet._is_valid_headers(
                df.columns,
                _REQ_INPUT_HEADERS_BMS,
                has_normalized_fields=False
                ):
            raise RuntimeError("[ERROR] BMS headers:\n {} \nDoes not match "
                "configuration headers:\n {}".format(', '.join(df.columns.tolist()),', '.join(
                 _REQ_INPUT_HEADERS_BMS)))

        return cls(
            df.to_dict('records'),
            std_header_map
            )
        # end by sypks

    def _rename_to_std(self, df):
        df.columns = self._std_header_map.values()

    @staticmethod
    def _to_std_headers(headers: List[str]) -> List[str]:
        '''
        Removes all punctuation characters, spaces, and converts to all
        lowercase characters. Returns standardized headers to be used
        internally
        '''
        delete_dict = {sp_char: '' for sp_char in string.punctuation}
        delete_dict[' '] = '' # space char not in sp_char by default
        trans_table = str.maketrans(delete_dict)

        return [sh.translate(trans_table).lower() for sh in headers]


    @staticmethod
    def _is_valid_headers(
            headers: List[str],
            required_input_headers: List[str], 
            has_normalized_fields: bool= False
            ) -> bool:
        '''
        Checks column names from loadsheet or BMS file are valid as
        defined in _REQ_INPUT_HEADERS and _REQ_OUTPUT_HEADERS
        '''
        trans_headers = Loadsheet._to_std_headers(headers)
        if has_normalized_fields:

            return set(required_input_headers+_REQ_OUTPUT_HEADERS) == \
                set(required_input_headers+_REQ_OUTPUT_HEADERS).intersection(
                    set(trans_headers))
        else:
            return set(required_input_headers) == \
                set(required_input_headers).intersection(set(trans_headers))

    @staticmethod
    def _to_std_header_mapping(
            orig_headers: List[str]
            ) -> Dict[str,str]:
        '''
        Creates a dict mapping from orig headers to strandardized
        headers used interally
        '''
        std_headers = Loadsheet._to_std_headers(orig_headers)
        return {std: orig for (std,orig) in zip(std_headers,orig_headers)}

    def get_std_header(
            self,
            header: str
            ) -> str:
        """
        Returns standardized header used internally based on the document
        header passed in
        """
        return self._std_header_map[header]

    def get_data_row(
            self,
            row: int
            ) -> Dict[str, Any]:
        pass

    def get_data_row_generator(self):
        pass

    def export_to_loadsheet(self, output_filepath):
        """
        exports data in Loadsheet object to excel file
        args:
            output_filepath - location and name of excel file output
        """
        df = pd.DataFrame.from_records(self._data)
        df = self._order_data(df)
        df.columns = [self._std_header_map[c] for c in df.columns]
        df.to_excel(output_filepath, index=False)
        try:
            self.create_pivot_table(output_filepath)
        except Exception as e:
            print("Couldn't create a ivot table.")


    def validate(
                self,
                non_null_fields: Optional[List[str]]= None
                ):
        """ Perform loadsheet validation. It will not validate the
        contents of the loadsheet, in terms of validity of entries, but
        will validate that all required fields are filled in and that
        no data is missing; the representations layer will handle the
        ontology checks.

        Checks:
         1) Required is always in {YES, NO}
         2) non-null fields are filled in where required is YES
         3) there are no duplicate fullAssetPath-standardFieldName pairs

         Args:
             non_null_fields - fields that are checked to have values in step 2
                              by default set to None to use the following:
                                  'building',
                                  'generalType',
                                  'assetName',
                                  'fullAssetPath',
                                  'standardFieldName',
                                  'deviceId',
                                  'objectType',
                                  'objectId',
                                  'units'
        Returns:
            None, but throws errors if any issues encountered
        """

        # non_null_fields arg included for future user definied check to
        # be implemented. Initial commit does not implement this feature
        # Therefore we use the hardcoded non_null_fields below
        if non_null_fields is None:
            non_null_fields	= [
                    'building',
                    'generaltype',
                    'assetname',
                    'fullassetpath',
                    'standardfieldname',
                    'deviceid',
                    'objecttype',
                    'objectid',
                    'units',
                    'ismissing'
                    ]

        # convert self._data to pd.DataFrame (we will transistion to
        # using only dataframes internally in a future update)
        df = pd.DataFrame.from_records(self._data)

        #required is always in [YES, NO]
        assert self._ensure_required_correct(df), "Unacceptable values in required column"

        #check for null field_details
        null_fields = self._find_null_fields(df, non_null_fields)
        assert len(null_fields) == 0, '\n'.join(
                      ["There are rows with missing fields:"]+
                      [f"\t\t{uid + 2}" for uid in null_fields]
                     )

        #check for duplicate fullAssetPath-standardFieldName combos
        repeat_uid = self._get_duplicate_asset_fields(df)
        assert len(repeat_uid) == 0, '\n'.join(
                      ["There are duplicated asset-field combinations:"]+
                      [f"\t\t{uid}" for uid in repeat_uid]
                     )

    def validate_without_errors(
                self,
                non_null_fields: Optional[List[str]]= None
                ):
            """
            Perform loadsheet validation as in validate
            but prints error messages instead of throwing errors
            """
            # non_null_fields arg included for future user definied check to
            # be implemented. Initial commit does not implement this feature
            # Therefore we use the hardcoded non_null_fields below
            if non_null_fields is None:
                non_null_fields	= [
                        'building',
                        'generaltype',
                        'assetname',
                        'fullassetpath',
                        'standardfieldname',
                        'deviceid',
                        'objecttype',
                        'objectid',
                        'units', 
                        'ismissing'
                        ]

            # convert self._data to pd.DataFrame (we will transistion to
            # using only dataframes internally in a future update)
            df = pd.DataFrame.from_records(self._data)

            #required is always in [YES, NO]
            if not self._ensure_required_correct(df):
                print("[ERROR]\tUnacceptable values in required column")

            #check for null field_details
            null_fields = self._find_null_fields(df, non_null_fields)
            if len(null_fields) > 0:
                print(f"[ERROR]\tThere are rows with missing fields:")
                for uid in null_fields:
                    print(f"\t\t{uid}")

            #check for duplicate fullAssetPath-standardFieldName combos
            repeat_uid = self._get_duplicate_asset_fields(df)
            if len(repeat_uid) > 0:
                print(f"[ERROR]\tThere are duplicated asset-field combinations:")
                for uid in repeat_uid:
                    print(f"\t\t{uid}")

    @staticmethod
    def _ensure_required_correct(
            data: pd.DataFrame
            ) -> bool:
        '''
        checks that required is in {YES, NO}
        '''
        return len(data[~data['required'].isin(['YES', 'NO'])]) == 0

    @staticmethod
    def _find_null_fields(
            data: pd.DataFrame,
            non_null_fields: list
            ) -> List[str]:
        '''
        Checks for null fields in any row marked required = YES
        '''
        needed_columns = ['required']
        needed_columns.extend(non_null_fields)
        relevant_df = data[needed_columns]
        relevant_df = relevant_df[(relevant_df['required'] == 'YES') & (relevant_df['ismissing'] == 'NO')]
        null_data = relevant_df[relevant_df.isnull().any(axis=1)]
        return null_data.index.tolist()

    @staticmethod
    def _get_duplicate_asset_fields(
            data: pd.DataFrame
            ) -> List[str]:
        '''
        finds and returns a list of duplicate FullAssetPath-StandardFieldName pairs
        '''
        data['uid'] = data['fullassetpath'] + ' ' + data['standardfieldname']
        df = data[data['required'] == 'YES']
        counts = df['uid'].value_counts()
        df_counts = pd.DataFrame({'uid':counts.index, 'amt':counts.values})
        repeat_uid = df_counts[df_counts['amt'] > 1]['uid'].tolist()
        return repeat_uid

    def apply_rules(
                self,
                rule_file: Dict
                ) -> None:
            """
            Apply rules to the dataset. Will ignore any field where
            manuallyMapped is set to YES.

            args:
                - rule_file: path to the rule file

            returns: N/A

            Note - See rules/rules.py for further information
            """
            r = Rules(rule_file)
            for row in self._data:
                #add output headers
                for orig, std in zip(_REQ_OUTPUT_HEADERS_ORIG, _REQ_OUTPUT_HEADERS):
                    if std not in row.keys():
                        row[std] = ""
                    if std not in self._std_header_map.keys():
                        self._std_header_map[std] = orig

                #add manuallyMapped
                if 'manuallymapped'not in row.keys():
                    row['manuallymapped'] = ''				
                if 'manuallymapped'not in  self._std_header_map.keys():
                    self._std_header_map['manuallymapped'] = "manuallyMapped"


                #skip manuallyMapped rows
                if row['manuallymapped'] == 'YES':
                    continue
                #apply rules
                else:
                    r.ApplyRules(row)

if __name__ == '__main__':
    k = Loadsheet.from_bms(r'C:\Users\ShaneSpencer\Downloads\OnboardingTool-master\OnboardingTool-master\resources\bms_exports\alc\US-MTV-1395.csv')