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

import unittest as ut
import representations as reps
import csv


class TestRepresentationsMethods(ut.TestCase):
	def setUp(self):
		self.asset = reps.Asset("bldg1", "gT", "", "asset1", "asset_path1")

		self.field = reps.Field("fN",
								 {"bms_type":"ALC",
								  "location":"l",
								  "controlProgram":"cP",
								  "name":"n",
								  "path":"p",
								  "type":"t"},
								 {"deviceId":"dID",
								  "objectId":"oID",
								  "objectName":"oN",
								  "objectType":"oT",
								  "units":"u"},
								 "",
								 False)
		self.assets = reps.Assets()

	"""Asset Tests"""
	def test_add_field(self):
		#add field to asset through method
		self.asset.add_field("fN",
							 {"bms_type":"ALC",
							  "location":"l",
							  "controlProgram":"cP",
							  "name":"n",
							  "path":"p",
							  "type":"t"},
							 {"deviceId":"dID",
							  "objectId":"oID",
							  "objectName":"oN",
							  "objectType":"oT",
							  "units":"u"},
							 "",
							 False)

		dump = self.asset.dump()

		expected = {'building': 'bldg1',
					'general_type': 'gT',
					'type_name': '',
					'asset_name':
					'asset1',
					'full_asset_name': 'asset_path1',
					'fields': {
						'fN': {
							'bms_info':
								{'bms_type': 'ALC',
								 'location': 'l',
								 'controlProgram': 'cP',
								 'name': 'n', 'path': 'p',
								 'type': 't'},
							'bacnet_address':
							 	{'deviceId': 'dID',
								 'objectId': 'oID',
								 'objectName': 'oN',
								 'objectType': 'oT',
								 'units': 'u'
								},
							'manually_mapped': ''
							}
						}
					}

		self.assertEqual(dump, expected)

	def test_update_field(self):
		self.asset.add_field("fN",
							 {"bms_type":"ALC",
							  "location":"l",
							  "controlProgram":"cP",
							  "name":"n",
							  "path":"p",
							  "type":"t"},
							 {"deviceId":"dID",
							  "objectId":"oID",
							  "objectName":"oN",
							  "objectType":"oT",
							  "units":"u"},
							 "",
							 False)
		self.asset.update_field("fN",
							 {"bms_type":"BLC",
							  "location":"ll",
							  "controlProgram":"cP",
							  "name":"n",
							  "path":"p",
							  "type":"t"},
							 {"deviceId":"dID",
							  "objectId":"oID",
							  "objectName":"oN",
							  "objectType":"oT",
							  "units":"u"},
							 "")
		dump = self.asset.dump()

		expected = {'building': 'bldg1',
					'general_type': 'gT',
					'type_name': '',
					'asset_name':
					'asset1',
					'full_asset_name': 'asset_path1',
					'fields': {
						'fN': {
							'bms_info':
								{'bms_type': 'BLC',
								 'location': 'll',
								 'controlProgram': 'cP',
								 'name': 'n', 'path': 'p',
								 'type': 't'},
							'bacnet_address':
							 	{'deviceId': 'dID',
								 'objectId': 'oID',
								 'objectName': 'oN',
								 'objectType': 'oT',
								 'units': 'u'
								},
							'manually_mapped': ''
							}
						}
					}
		self.assertEqual(dump, expected)

		with self.assertRaises(AssertionError):
			self.asset.update_field("fNN",
								 {"bms_type":"BLC",
								  "location":"ll",
								  "controlProgram":"cP",
								  "name":"n",
								  "path":"p",
								  "type":"t"},
								 {"deviceId":"dID",
								  "objectId":"oID",
								  "objectName":"oN",
								  "objectType":"oT",
								  "units":"u"},
								 "")

	def test_update_type(self):
		self.asset.update_type("new_type")
		self.assertEqual("new_type", self.asset.type_name)

	def test_remove_field(self):
		self.asset.add_field("fN",
							 {"bms_type":"ALC",
							  "location":"l",
							  "controlProgram":"cP",
							  "name":"n",
							  "path":"p",
							  "type":"t"},
							 {"deviceId":"dID",
							  "objectId":"oID",
							  "objectName":"oN",
							  "objectType":"oT",
							  "units":"u"},
							 "",
							 False)

		with self.assertRaises(AssertionError):
				self.asset.remove_field("fNN")

		self.asset.remove_field("fN")

		dump = self.asset.dump()
		expected = {'building': 'bldg1', 'general_type': 'gT', 'type_name': '', 'asset_name': 'asset1', 'full_asset_name': 'asset_path1', 'fields': {}}

		self.assertEqual(expected, dump)

	"""Field Tests"""
	def test_get_field_details(self):
		details = self.field.get_field_details()
		expected = {"bms_info":{"bms_type":"ALC",
					 "location":"l",
					 "controlProgram":"cP",
					 "name":"n",
					 "path":"p",
					 "type":"t"},
					"bacnet_address":{"deviceId":"dID",
					 "objectId":"oID",
					 "objectName":"oN",
					 "objectType":"oT",
					 "units":"u"},
					"manually_mapped":""}

		self.assertEqual(expected, details)

	def test_add_placeholder_field(self):
		placeholder_field = reps.Field("","","","",True)
		details = placeholder_field.get_field_details()
		expected = {"bms_info":{'bms_type':"",'location':'', 'controlProgram':'', 'name':'Placeholder', 'path':'', 'type':''},
					"bacnet_address":{'deviceId':'', 'objectId':'', 'objectName':'Placeholder', 'objectType':'', 'units':''},
					"manually_mapped":""}
		self.assertEqual(expected, details)

	"""Assets tests"""
	'''
	update type, add field, remove field, get_general_type
	all just call single asset function
	tested above, additional testing not needed
	'''
	def test_add_asset(self):
		#adding asset and checking dump
		self.assets.add_asset("bldg1", "gT", "", "asset1", "asset_path1")
		self.assets.assets['asset_path1'].add_field("fN",
							 {"bms_type":"ALC",
							  "location":"l",
							  "controlProgram":"cP",
							  "name":"n",
							  "path":"p",
							  "type":"t"},
							 {"deviceId":"dID",
							  "objectId":"oID",
							  "objectName":"oN",
							  "objectType":"oT",
							  "units":"u"},
							 "",
							 False)

		dump = self.assets.dump_to_data()
		expected  =[{'location': 'l', 'controlProgram': 'cP', 'name': 'n', 'type': 't',
					'path': 'p', 'deviceId': 'dID', 'objectType': 'oT', 'objectId': 'oID',
					'objectName': 'oN', 'units': 'u', 'required': 'YES', 'manuallyMapped': '',
					'building': 'bldg1', 'generalType': 'gT', 'typeName': '',
					'assetName': 'asset1', 'fullAssetPath': 'asset_path1', 'standardFieldName': 'fN'}]

		self.assertEqual(expected, dump)

		with self.assertRaises(AssertionError):
			self.assets.add_asset("bldg1", "gT", "", "asset1", "asset_path1")

	def test_remove_asset(self):
		self.assets.add_asset("bldg1", "gT", "", "asset1", "asset_path1")
		self.assets.assets['asset_path1'].add_field("fN",
							 {"bms_type":"ALC",
							  "location":"l",
							  "controlProgram":"cP",
							  "name":"n",
							  "path":"p",
							  "type":"t"},
							 {"deviceId":"dID",
							  "objectId":"oID",
							  "objectName":"oN",
							  "objectType":"oT",
							  "units":"u"},
							 "",
							 False)

		with self.assertRaises(AssertionError):
			self.assets.remove_asset("asset_path2")

		self.assets.remove_asset("asset_path1")
		self.assertEqual([], self.assets.dump_to_data())

	def test_get_all_asset_fields(self):
		self.assets.add_asset("bldg1", "gT", "", "asset1", "asset_path1")
		self.assets.assets['asset_path1'].add_field("fN",
							 {"bms_type":"ALC",
							  "location":"l",
							  "controlProgram":"cP",
							  "name":"n",
							  "path":"p",
							  "type":"t"},
							 {"deviceId":"dID",
							  "objectId":"oID",
							  "objectName":"oN",
							  "objectType":"oT",
							  "units":"u"},
							 "",
							 False)
		self.assets.assets['asset_path1'].add_field("fN2a",
							 {"bms_type":"ALC",
							  "location":"l",
							  "controlProgram":"cP",
							  "name":"n",
							  "path":"p",
							  "type":"t"},
							 {"deviceId":"dID",
							  "objectId":"oID",
							  "objectName":"oN",
							  "objectType":"oT",
							  "units":"u"},
							 "",
							 False)


		self.assets.add_asset("bldg2", "gT", "", "asset2", "asset_path2")
		self.assets.assets['asset_path2'].add_field("fN",
							 {"bms_type":"ALC",
							  "location":"l",
							  "controlProgram":"cP",
							  "name":"n",
							  "path":"p",
							  "type":"t"},
							 {"deviceId":"dID",
							  "objectId":"oID",
							  "objectName":"oN",
							  "objectType":"oT",
							  "units":"u"},
							 "",
							 False)
		self.assets.assets['asset_path2'].add_field("fN2",
							 {"bms_type":"ALC",
							  "location":"l",
							  "controlProgram":"cP",
							  "name":"n",
							  "path":"p",
							  "type":"t"},
							 {"deviceId":"dID",
							  "objectId":"oID",
							  "objectName":"oN",
							  "objectType":"oT",
							  "units":"u"},
							 "",
							 False)


		fields = self.assets.get_all_asset_fields()
		expected = {'fN2', 'fN2a', 'fN'}

		self.assertEqual(expected, fields)

	def test_get_general_types(self):
		self.assets.add_asset("bldg1", "gT1", "", "asset1", "asset_path1")
		self.assets.add_asset("bldg2", "gT2", "", "asset2", "asset_path2")
		self.assets.add_asset("bldg3", "gT2", "", "asset3", "asset_path3")
		self.assets.add_asset("bldg4", "gT3", "", "asset4", "asset_path4")

		res = self.assets.get_general_types()
		expected = {'gT1', 'gT2', 'gT3'}

		self.assertEqual(expected, res)


if __name__ == '__main__':
    ut.main()
