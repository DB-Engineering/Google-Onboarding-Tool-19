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

from typing import Optional
from typing import Union
from typing import Dict
from typing import List
from typing import Any

# Open-source Packages
import openpyxl
import pandas as pd

sys.path.append('../')

# Proprietary Packages
from rules.rules import Rules

# Module GOBAL and CONTRAINTS
LOADSHEET_DEFAULT_CONFIG = 'loadsheet_default_config.ini'  # TODO: Not used but will be added in future

_REQ_INPUT_HEADERS = [
		"location",
		"controlProgram",
		"name",
		"type",
		"path",
		"objectId",
		"objectType",
		"deviceId",
		"objectName",
		'units'
		]

_REQ_OUTPUT_HEADERS = [
		'required',
		'manuallyMapped',
		'building',
		'generalType',
		'typeName',
		'assetName',
		'fullAssetPath',
		'standardFieldName'
		]

_INPUT_HEADER_MAP = {
		"Location":"location",
		"Control Program":"controlProgram",
		"Name":"name",
		"Type":"type",
		"Path":"path",
		"Object ID":"objectId",
		"Object Type":"objectType",
		"Device ID":"deviceId",
		"Object Name":"objectName",
		'Units':'units'
		}

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
	"""

	def __init__(
			self,
			data: List[Dict[str,Any]]= list(dict())
			):
		self._data = data

		''' # this functionality is not currently supported for initial
			# commit. ini_config_filepath arg has been included for
			# future feature implementation 07062020 by sypks
		_REQ_INPUT_HEADERS = self._load_ini_config(
				section= 'required input header',
				config_file_path= config_file_path,
				return_key_only= True
				)
		_REQ_OUTPUT_HEADERS = self._load_ini_config(
				section= 'required output header',
				config_file_path= config_file_path,
				return_key_only= True)
		self._map_input_headers = self._load_ini_config(
				section= 'required input header',
				config_file_path= config_file_path
				)
		'''


	@classmethod
	def from_loadsheet(
			cls,
			filepath: str,
			ini_config_filepath: str= 'loadsheet_default_config.ini'
			):
		"""
		Initializes loadsheet object from existing loadsheet Excel file
		args:
			filepath - absolute filepath to loadsheet excel file
			ini_config_filepath - not currently enabled, do not use
		returns:
			loadsheet object
		"""
		# hardcode header rows as [0,1] for initial release
		df = pd.read_excel(filepath, header= [0])

		# get_level_values(1) returns the 2nd index of multi-index
		#df.columns = df.columns.get_level_values(0)
		assert cls._is_valid_headers(df.columns, "Loadsheet") == True, \
				"[ERROR] loadsheet headers: " +\
				"{} do not match configuration headers: {}".format(', '.join(df.columns),
				', '.join(_REQ_INPUT_HEADERS+_REQ_OUTPUT_HEADERS))

		return cls(df.to_dict('records'))

	@classmethod
	def from_bms(
			cls,
			filepath: str,
			ini_config_filepath: str= 'loadsheet_default_config.ini'
			):
		"""
		Initializes loadsheet object from existing BMS file
		args:
			filepath - absolute filepath to BMS file
			ini_config_filepath - not currently enabled, do not use
		returns:
			loadsheet object
		"""
		# hardcode header as row 0 for inital release
		df = pd.read_csv(filepath, header= 0)

		assert cls._is_valid_headers(df.columns, "ALC") == True, \
				"Error loadsheet headers: {} do not match configuration ".format(', '.join(df.columns)) +\
				"headers: {}".format(', '.join(_REQ_INPUT_HEADERS+_REQ_OUTPUT_HEADERS))

		return cls(df.to_dict('records'))

	@staticmethod
	def _is_valid_headers(headers: List[str], filetype: str) -> bool:
		'''
		Checks column names from loadsheet or BMS file are valid
		as defined in _REQ_INPUT_HEADERS and _REQ_OUTPUT_HEADERS
		'''
		supported_filetypes = ['Loadsheet', 'ALC']
		assert filetype in supported_filetypes, "[ERROR]\tFiletype not supported"

		if filetype == 'Loadsheet':
			return set([h.lower().replace(' ','') for h in _REQ_INPUT_HEADERS+_REQ_OUTPUT_HEADERS]).\
					   issubset(set([h.lower().replace(' ','') for h in headers]))
		if filetype == 'ALC':
			return set([h.lower().replace(' ','') for h in _REQ_INPUT_HEADERS]).\
					   issubset(set([h.lower().replace(' ','') for h in headers]))

	# _load_ini_config feature currently not implemented for initial
	# commit removed 07062020 by sypks
	'''
	def _load_ini_config(
			self,
			section: str,
			ini_config_filepath: str,
			return_key_only: bool= False
			):
		# initilize and read config_file_path, key-with-no-value ok
				config = cp.RawConfigParser(allow_no_value= True)
				config.optionxform = str # specify keys to be case-sensitive
				config.read(ini_config_file_path)

				# check for valid section in config_file_path
				assert config.has_section(section) == True, \
							 'configuration file does not contain section: %s' % section

				# return either (key,value) pair or just the key based on
				# boolean value of return_key_only
				if not return_key_only:
						return {key: value for key, value in config.items(section)}
				else:
						return [key for key, _ in config.items(section)]
	'''

	def export_to_loadsheet(self, output_filepath):
		"""
		exports data in Loadsheet object to excel file
		args:
			output_filepath - location and name of excel file output
		"""
		df = pd.DataFrame.from_records(self._data)
		df.to_excel(output_filepath, index=False)

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
					'generalType',
					'assetName',
					'fullAssetPath',
					'standardFieldName',
					'deviceId',
					'objectType',
					'objectId',
					'units'
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
					  [f"\t\t{uid}" for uid in null_fields]
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
						'generalType',
						'assetName',
						'fullAssetPath',
						'standardFieldName',
						'deviceId',
						'objectType',
						'objectId',
						'units'
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
		relevant_df = relevant_df[relevant_df['required'] == 'YES']
		null_data = relevant_df[relevant_df.isnull().any(axis=1)]
		return null_data.index.tolist()

	@staticmethod
	def _get_duplicate_asset_fields(
			data: pd.DataFrame
			) -> List[str]:
		'''
		finds and returns a list of duplicate FullAssetPath-StandardFieldName pairs
		'''
		data['uid'] = data['fullAssetPath'] + ' ' + data['standardFieldName']
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
				if row['manuallyMapped'] == 'YES':
					continue
				else:
					r.ApplyRules(row)
