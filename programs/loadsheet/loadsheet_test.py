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

import unittest
import loadsheet as ls
import pandas


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

class TestLoadsheetMethods(unittest.TestCase):
	def setUp(self):
		#creates a DataFrame with one generic row
		self.df = pandas.DataFrame(columns = _REQ_INPUT_HEADERS + _REQ_OUTPUT_HEADERS)
		self.df.loc[0] = ['L','C','N','T','P','OID','OT','DID','ON','U','r','mM','b','gT','tN','aN','fAP','sFN']

	def test_ensure_required(self):
		#tests the _ensure_required_correct method of the Loadsheet class
		#passes required as YEES and passes required as None
		self.df.at[0,'required'] = 'YEES'
		self.df.loc[1] = ['L','C','N','T','P','OID','OT','DID','ON','U', None,'mM','b','gT','tN','aN', 'fAP','sFN']

		self.assertFalse(ls.Loadsheet._ensure_required_correct(self.df))

	def test_find_null(self):
		#tests the _find_null_fields method of the Loadsheets class
		#passes a DataFrame with
		#	required = NO and nulls
		#	required = YES and non-required nulls
		#	and required = YES and each required null field

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

		self.df.loc[0] = ['L','C','N','T','P','OID','OT','DID','ON','U','NO','mM',None,'gT','tN','aN','fAP','sFN']
		self.df.loc[1] = [None,'C','N','T','P','OID','OT','DID','ON','U','YES','mM','b','gT','tN','aN', 'fAP','sFN']
		self.df.loc[2] = ['L','C','N','T','P','OID','OT','DID','ON','U','YES','mM',None,'gT','tN','aN','fAP','sFN']
		self.df.loc[3] = ['L','C','N','T','P','OID','OT','DID','ON','U','YES','mM','b',None,'tN','aN','fAP','sFN']
		self.df.loc[4] = ['L','C','N','T','P','OID','OT','DID','ON','U','YES','mM','b','gT','tN',None,'fAP','sFN']
		self.df.loc[5] = ['L','C','N','T','P','OID','OT','DID','ON','U','YES','mM','b','gT','tN','aN',None,'sFN']
		self.df.loc[6] = ['L','C','N','T','P','OID','OT','DID','ON','U','YES','mM','b','gT','tN','aN','fAP',None]
		self.df.loc[7] = ['L','C','N','T','P','OID','OT',None,'ON','U','YES','mM','b','gT','tN','aN','fAP','sFN']
		self.df.loc[8] = ['L','C','N','T','P','OID',None,'DID','ON','U','YES','mM','b','gT','tN','aN','fAP','sFN']
		self.df.loc[9] = ['L','C','N','T','P',None,'OT','DID','ON','U','YES','mM','b','gT','tN','aN','fAP','sFN']
		self.df.loc[10] = ['L','C','N','T','P','OID','OT','DID','ON',None,'YES','mM','b','gT','tN','aN','fAP','sFN']

		self.assertEqual([2,3,4,5,6,7,8,9,10], ls.Loadsheet._find_null_fields(self.df, non_null_fields))

	def test_get_dupes(self):
		#tests the _get_duplicate_asset_fields method of the Loadsheet class
		#passes a DataFrame with duplicate fullAssetPath-standardFieldName pairs
		self.df.loc[1] = ['L','C','N','T','P','OID','OT','DID','ON','U','YES','mM','b','gT','tN','aN','fAP','sFN']
		self.df.loc[2] = ['L','C','N','T','P','OID','OT','DID','ON','U','YES','mM','b','gT','tN','aN','fAP','sFN']
		self.df.loc[3] = ['L','C','N','T','P','OID','OT','DID','ON','U','YES','mM','b','gT','tN','aN','fullAssetPath','sFN']
		self.df.loc[4] = ['L','C','N','T','P','OID','OT','DID','ON','U','NO','mM','b','gT','tN','aN','fullAssetPath','sFN']

		self.assertEqual(["fAP sFN"], ls.Loadsheet._get_duplicate_asset_fields(self.df))


if __name__ == '__main__':
    unittest.main()
