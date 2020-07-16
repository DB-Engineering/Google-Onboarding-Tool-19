import unittest as ut
import representations as reps


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


	#Field Tests
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

		self.assertEquals(expected, details)

	def test_add_placeholder_field(self):
		placeholder_field = reps.Field("","","","",True)
		details = placeholder_field.get_field_details()
		expected = {"bms_info":{'bms_type':"",'location':'', 'controlProgram':'', 'name':'Placeholder', 'path':'', 'type':''},
					"bacnet_address":{'deviceId':'', 'objectId':'', 'objectName':'Placeholder', 'objectType':'', 'units':''},
					"manually_mapped":""}
		self.assertEqual(expected, details)

	#Assets tests
	def test_

if __name__ == '__main__':
    ut.main()
