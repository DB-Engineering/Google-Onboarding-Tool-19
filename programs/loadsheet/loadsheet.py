__version__ = '0.0.3'
__author__ = 'Trevor S., Shane S., Andrew K.'

# Standard Packages
import os
import sys
import string

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

_REQ_INPUT_HEADERS = [
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
			data: List[Dict[str,Any]]= list(dict()),
			is_loadsheet: bool= False
			):
		assert Loadsheet._is_valid_headers(data.keys(), is_loadsheet) == True,\
				"[ERROR] loadsheet headers:\n {} \ndo not match configuration \
				headers:\n {}".format(', '.join(df.columns),', '.join(
					[_REQ_INPUT_HEADERS+_REQ_OUTPUT_HEADERS if is_loadsheet 
					else _REQ_INPUT_HEADERS]))
		self._data = data
		self._std_header_map = Loadsheet._to_standardized_header_mapping(
				data.keys())

	@classmethod
	def from_loadsheet(
			cls,
			filepath: str
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
		df = pd.read_excel(filepath, header= 0)
		return cls(df.to_dict('records'))

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
		# hardcode header as row 0 for inital release
		df = pd.read_csv(filepath, header= 0)
		return cls(df.to_dict('records'))

	@staticmethod
	def _to_std_headers(headers: List[str]) -> List[str] -> List[str]:
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
	def _is_valid_headers(headers: List[str], is_loadsheet: bool) -> bool:
		'''
		Checks column names from loadsheet or BMS file are valid as 
		defined in _REQ_INPUT_HEADERS and _REQ_OUTPUT_HEADERS
		'''
		if is_loadsheet:
			return set([h.lower().replace(' ','') for h in _REQ_INPUT_HEADERS+_REQ_OUTPUT_HEADERS]).\
					   issubset(set([h.lower().replace(' ','') for h in headers]))
		else:
			return set([h.lower().replace(' ','') for h in _REQ_INPUT_HEADERS]).\
					   issubset(set([h.lower().replace(' ','') for h in headers]))

	@staticmethod
	def _to_std_header_mapping(
			orig_headers: List[str]
			) -> Dict[str,str]:
		'''
		Creates a dict mapping from orig headers to strandardized 
		headers used interally
		'''
		std_headers = Loadsheet._to_std_headers(orig_headers)
		return {orig: std for (std,orig) in zip(std_headers,orig_headers)}

	def get_std_header(
			self,
			header: str
			) -> str:
		"""
		Returns standardized header used internaly baed on the document 
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
