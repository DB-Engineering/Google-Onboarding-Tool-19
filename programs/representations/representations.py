fload_from
import json
import base64

import sys
sys.path.append('../')

import ontology.ontology
from pretty import PrettyPrint

def _convert_to_base64(data):
	"""
	Convert a data object into a base64 message.
	Used as a codeword to uniquely identify each asset
	"""

	if isinstance(data,set):
		data = list(data)
		data.sort()
		data = tuple(data)
		data = str(data)

	if isinstance(data,list):
		data.sort()
		data = tuple(data)
		data = str(data)

	if isinstance(data,tuple):
		data = str(data)

	encoded_bytes = base64.b64encode(data.encode("utf-8"))
	encoded_str = str(encoded_bytes, "utf-8")

	return encoded_str

class Asset:
	""" An asset model for the loadsheet data. Holds all the relevant loadsheet asset-related data
	and serves as a wrapper for the Field class, allowing user to add/update fields directly on the
	asset object. """

	def __init__(self,building,general_type,type_name,asset_name,full_asset_name):
		"""
		Initialize the model

		args:
			- building: string building name
			- general_type: string asset type e.g. VAV
			- type_name: Unique name for type definitions
			- asset_name: string physical name
			- full_asset_name: BMS internal name

		returns: new asset objects
		"""

		self.building = building
		self.general_type = general_type
		self.type_name = type_name
		self.asset_name = asset_name
		self.full_asset_name = full_asset_name
		self.fields = {}
		self.matched = False

	def add_field(self,field_name,bms_info,bacnet_address,manually_mapped=False,placeholder=False):
		"""
		Adds a field to the asset object

		args:
			- field_name: string point name
			- bms_info: dictionary, describing bms type, location, controlProgram,
					    name, path, and type
			- bacnet_address: dictionary describing deviceId, objectId,
							  objectName, objectType, and units
			- manuallyMapped: flag if field is manually filled in, set false by default
			- placeholder: flag for placeholder field creation, default false

		returns: N/A
		"""
		assert field_name not in self.fields, "Field {} already set.".format(field_name)
		self.fields[field_name] = Field(field_name,bms_info,bacnet_address,manually_mapped, placeholder)

	def update_field(self,field_name,bms_info,bacnet_address,manually_mapped=False):
		"""
		Update a field on the asset.

		args:
			- field_name: string point name
			- bms_info: dictionary, describing bms type, location, controlProgram,
					    name, path, and type
			- bacnet_address: dictionary describing deviceID, objectID,
							  objectName, objectType, and units
			- manuallyMapped: flag if field is manually filled in, set false by default


		returns: N/A
		"""
		assert field_name in self.fields, "Field not defined."
		del self.fields[field_name]
		self.fields[field_name] = Field(field_name,bms_info,bacnet_address,manually_mapped)

	def update_type(self,type_name):
		"""
		Sets the type_name.

		args:
			- type_name: #TODO

		returns: N/A
		"""
		self.type_name = type_name

	def remove_field(self,field_name):
		"""
		Remove a field from the asset.

		args:
			- field_name: string point name to be removed

		returns: N/A
		"""
		assert field_name in self.fields, "Field not defined; cannot remove."
		del self.fields[field_name]

	def get_general_type(self):
		"""
		Get the general type for the asset.

		returns: general_type string
		"""
		return self.general_type

	def get_fields(self):
		"""
		Get the field names on the asset.

		returns: list of field name strings
		"""
		return [field for field in self.fields]

	def get_field_details(self,field_name):
		"""
		Get the details for a specified field.

		args:
			- field_name: string field name to retrieve

		returns: dictionary of BMS info of passed field
		"""
		assert field_name in self.fields, "Field not defined; cannot find."
		return self.fields[field_name].get_field_details()

	def get_all_field_details(self):
		"""
		Get the details for all fields on the asset.

		returns: dictionary of BMS info for all fields
		"""
		field_details = {}
		for field in self.fields:
			field_details[field] = self.fields[field].get_field_details()
		return field_details

	def get_asset_details(self):
		"""
		Get all the asset details stored in the object.

		returns: dictionary of asset details
		"""
		asset_details = {
				'building':self.building,
				'general_type':self.general_type,
				'type_name':self.type_name,
				'asset_name':self.asset_name,
				'full_asset_name':self.full_asset_name
			}
		return asset_details

	def add_match(self, match):
		"""
		adds match to asset

		args:
			- match: match object to connect
		"""
		self.match = match
		self.matched = True

	def apply_match(self):
		"""
		applies match object details to the asset
		adds necessary placeholder fields and updates name
		"""

		if self.matched:
			#apply type names
			self.update_type(self.match.ont_type_name)

			#apply fields
			existing_fields = self.get_fields()
			for field in self.match.ont_type_fields:
				if field[0] not in existing_fields and field[1]:
					self.add_field(field[0], '', '', placeholder=True)

	def dump(self):
		"""
		Dump all asset details.

		returns: dictionary of asset and field details
		"""
		details = self.get_asset_details()
		details.update({'fields':self.get_all_field_details()})
		return details

class Field:
	""" A field model for the loadsheet data. Requires BMS specific metadata and BACnet address info. """
	#TODO: Add in BMS type functionality that spans the different classes

	def __init__(self,field_name,bms_info,bacnet_address,manually_mapped=False,placeholder=False):
		"""
		Initialize the model.

		args:
			- field_name: string point name
			- bms_info: dictionary, describing bms type, location, controlProgram,
					    name, path, and type
			- bacnet_address: dictionary describing deviceID, objectID,
							  objectName, objectType, and units
			- manuallyMapped: flag if field is manually filled in, set false by default
			- placeholder: flag for placeholder field creation, default false

		returns: field object
		"""
		self.field_name=field_name
		self.manually_mapped=manually_mapped
		if not placeholder:
			self.bms_info = bms_info
			assert 'bms_type' in self.bms_info, "Argument 'bms_info' requires a 'bms_type' key."

			if bms_info['bms_type'] == 'ALC':
				required_fields = ['location','controlprogram','name','type','path']
				for field in required_fields:
					assert field in self.bms_info, "Field '{}' not in 'bms_info' argument.".format(field)

			self.bacnet_address = bacnet_address

			bacnet_requirements = ['deviceid','objecttype','objectid','objectname','units']
			for field in bacnet_requirements:
				assert field in bacnet_requirements, "Field '{}' not in 'bacnet_address' argument.".format(field)

		else:
			self.bms_info={'bms_type':"",'location':'', 'controlprogram':'', 'name':'Placeholder', 'path':'', 'type':''}
			self.bacnet_address={'deviceId':'', 'objectId':'', 'objectName':'Placeholder', 'objectType':'', 'units':''}

	def get_field_details(self):
		"""
		Return all the field details in a single dictionary.

		returns: dictionary of BMS info of passed field
		"""
		details = {'bms_info':self.bms_info,'bacnet_address':self.bacnet_address,'manually_mapped':self.manually_mapped}
		return details

class Assets:
	"""
	A wrapper class to handle asset models. Holds all relevant loadsheet data for all
	asset object passed in.
	"""

	def __init__(self):
		""" Initialize the class. """
		self.assets = {}
		self.determined_types = {}
		self.ununsed_data = []

	def add_asset(self,building,general_type,type_name,asset_name,full_asset_name):
		"""
		Update an asset or add it if it doesnt exist yet.

		args:
			- building: string building name
			- general_type: string asset type e.g. VAV
			- type_name: unique name for type definitions
			- asset_name: string physical name
			- full_asset_name: BMS internal name
		"""
		assert full_asset_name not in self.assets, "Asset {} already exists.".format(full_asset_name)
		asset = Asset(building,general_type,type_name,asset_name,full_asset_name)
		self.assets[full_asset_name] = asset

	def remove_asset(self,full_asset_name):
		"""
		Remove an asset.

		args:
			- full_asset_name: name of asset to remove
		"""
		assert full_asset_name in self.assets, "Asset {} does not exist.".format(full_asset_name)
		del self.assets[full_asset_name]

	def update_type(self,full_asset_name,type_name):
		"""
		Update type of a given asset.

		args:
			- full_asset_name: name of asset to update
			- type_name: string type name to update asset to match
		"""
		self.assets[full_asset_name].update_type(type_name)

	def add_field(self,full_asset_name,field_name,bms_info,bacnet_address,manually_mapped=False):
		"""
		Add a field.

		args:
			- full_asset_name: name of asset to add field to
			- field_name: string point name
			- bms_info: dictionary, describing location, controlProgram,
						name, path, and type
			- bacnet_address: dictionary describing deviceID, objectID,
							  objectName, objectType, and units
			- manuallyMapped: flag if field is manually filled in, set false by default
		"""
		self.assets[full_asset_name].add_field(field_name,bms_info,bacnet_address,manually_mapped)

	def remove_field(self,full_asset_name,field_name):
		"""
		Remove a field.

		args:
			- full_asset_name: name  of asset to remove field from
			- field_name: string point name to be removed
		"""
		self.assets[full_asset_name].remove_field(field_name)

	def get_fields(self,full_asset_name):
		"""
		Get fields for an asset.

		args:
			- full_asset_name: name of asset ot get fields of

		returns: list of field objects
		"""
		return self.assets[full_asset_name].get_fields()

	def get_all_asset_fields(self):
		"""
		Get all distinct fields in all assets. Easy for validation.

		returns: list of unique fields in assets
		"""
		unique_fields = set()
		for asset in self.assets:
			fields = self.get_fields(asset)
			for field in fields:
				unique_fields.add(field)

		return unique_fields

	def get_general_type(self,full_asset_name):
		"""
		Get the general type for the asset.

		args:
			- full_asset_name: asset to get general_type of

		returns: general type of asset
		"""
		return self.assets[full_asset_name].get_general_type()

	def get_general_types(self):
		"""
		Get all general types defined for all assets.

		returns: list of all general types
		"""
		general_types = set()
		for asset in self.assets:
			gt = self.assets[asset].get_general_type()
			general_types.add(gt)

		return general_types

	def dump_asset(self,full_asset_name):
		"""
		Dump asset contents.

		args:
			- full_asset_name: asset to get dump

		results: full asset dump
		"""
		dump_details = self.assets[full_asset_name].dump()
		return dump_details

	def dump_all_assets(self):
		"""
		Dump all assets.

		returns: full data dump
		"""
		dump_details = {}
		for asset in self.assets:
			dump_details[asset] = self.dump_asset(asset)

		return dump_details

	def load_from_row(self,data_row):
		"""
		Load from a row of data.

		args:
			- data_row: row of data to add
		"""

		if data_row['fullassetpath'] not in self.assets:
			self.add_asset(
						data_row['building'],
						data_row['generaltype'],
						data_row['typename'],
						data_row['assetname'],
						data_row['fullassetpath']
					)

		bms_info = {
				'bms_type':'ALC',
				'location':data_row['location'],
				'controlprogram':data_row['controlprogram'],
				'name':data_row['name'],
				'type':data_row['type'],
				'path':data_row['path']
			}

		bacnet_address = {
				'deviceid':data_row['deviceid'],
				'objectid':data_row['objectid'],
				'objecttype':data_row['objecttype'],
				'objectname':data_row['objectname'],
				'units':data_row['units']
			}

		self.add_field(data_row['fullassetpath'],data_row['standardfieldname'],bms_info,bacnet_address,data_row['manuallymapped'])

	def load_from_data(self,data):
		"""
		Load from a data object.

		args:
			- data: dictionary of lists representing loadsheet data
		"""

		for row in data:
			if row['required'] == 'YES':
				self.load_from_row(row)
			else:
				self.ununsed_data.append(row)

	def dump_to_data(self):
		""" Dump the assets object into the original data format. Append any unused rows of data that were not applied
		to assets.

		returns: dictionary of lists representing loadsheet data
		"""
		# TODO: Create loadsheet config object set
		data = self.dump_all_assets()
		out_data = []
		for asset in data:
			for field in data[asset]['fields']:
				fullAssetPath = data[asset]['full_asset_name']
				assetName = data[asset]['asset_name']
				building = data[asset]['building']
				generalType = data[asset]['general_type']
				typeName = data[asset]['type_name']
				standardFieldName = field
				deviceId = data[asset]['fields'][field]['bacnet_address']['deviceid']
				objectId = data[asset]['fields'][field]['bacnet_address']['objectid']
				objectName = data[asset]['fields'][field]['bacnet_address']['objectname']
				objectType = data[asset]['fields'][field]['bacnet_address']['objecttype']
				units = data[asset]['fields'][field]['bacnet_address']['units']
				location = data[asset]['fields'][field]['bms_info']['location']
				controlProgram = data[asset]['fields'][field]['bms_info']['controlprogram']
				manually_mapped = data[asset]['fields'][field]['manually_mapped']
				name = data[asset]['fields'][field]['bms_info']['name']
				path = data[asset]['fields'][field]['bms_info']['path']
				ttype = data[asset]['fields'][field]['bms_info']['type']
				row = {
					'location':location,
					'controlprogram':controlProgram,
					'name':name,
					'type':ttype,
					'path':path,
					'deviceid':deviceId,
					'objecttype':objectType,
					'objectid':objectId,
					'objectname':objectName,
					'units':units,
					'required':'YES',
					'manuallymapped':manually_mapped,
					'building':building,
					'generaltype':generalType,
					'typename':typeName,
					'assetname':assetName,
					'fullassetpath':fullAssetPath,
					'standardfieldname':standardFieldName
				}
				out_data.append(row)
		if len(self.ununsed_data)>0:
			for row in self.ununsed_data:
				out_data.append(row)
		return out_data

	def determine_types(self):
		"""
		Use the unique fields for each asset to create a list of unique types.

		returns: list of unique types
		"""

		unique_types = {}

		for asset in self.assets:
			fields = self.get_fields(asset)
			general_type = self.get_general_type(asset)
			field_code = _convert_to_base64(fields)

			if field_code not in unique_types:
				unique_types[field_code] = {'general_type':general_type,'fields':fields,'assets':[asset]}

			else:
				unique_types[field_code]['assets'].append(asset)

		return unique_types

	def dump_to_steve_format(self):
		"""
		Dump the data content to the Steve format.

		args:
			-

		"""
		# TODO: Add functionality for this to CLI and Handler
		# Output for STEVE format.
		steve_headers = (
				'location','controlProgram','name','type','objectType','deviceId','objectName','units','path',
				'required','bacnetAvailable','building','generalType','assetName','fullAssetPath','standardFieldName'
			)

		data = self.dump_to_data()

		s = '\t'
		print(s.join(steve_headers))
		for row in data:
			out_row = {}
			for i in steve_headers:
				if i in row:
					if i == 'objectType':
						out_row['objectType'] = row['objectType'] +':'+str(row['objectId'])
					elif i == 'deviceId':
						out_row['deviceId'] = 'DEV:' + str(row['deviceId'])
					else:
						out_row[i] = row[i]
				else:
					out_row[i] = ''


			s = '\t'
			print(s.join(out_row.values()))

	def validate_without_errors(self, ontology):
		"""
		Validate the subfields and fields against the ontology.
		Only prints errors seen, but runs through everything

		args:
			- ontology: the ontology object to validate the assets against

		"""

		fields = self.get_all_asset_fields()

		invalid_subfields = ontology.check_subfields(fields)
		invalid_fields = ontology.check_fields(fields)

		has_errors = False
		if len(invalid_subfields)>0:
			has_errors = True
			print('Undefined subfields (define them or change them):')
			for subfield in invalid_subfields:
				print('\t{}'.format(subfield))

		if len(invalid_fields)>0:
			has_errors = True
			print('Undefined fields (define them or change them):')
			for field in invalid_fields:
				print('\t{}'.format(field))

		if has_errors == False:
			print("No representation errors!")

	def validate(self,ontology):
		"""
		Validate the type subfields and fields against the ontology.
		Throws errors when issue encountered

		args:
			- ontology: ontology object to check assets against

		"""

		fields = self.get_all_asset_fields()

		invalid_subfields = ontology.check_subfields(fields)
		invalid_fields = ontology.check_fields(fields)


		assert len(invalid_subfields) == 0, "Undefined subfields (define them or change them): {}".format(str(invalid_subfields))

		assert len(invalid_fields) == 0, "Undefined fields (define them or change them): {}".format(str(invalid_fields))

		print("[INFO]\tNo representation errors!")





### Test block.
if __name__ == '__main__':

	rows = [
			{'location': '/One city block/111 8th/5th Floor', 'controlProgram': 'AC-5-1 (Mail Room)','name': 'Comp Start', 'type': 'BMBO','path': '#1118th_ac-5-1/comp', 'deviceId': 2790529, 'objectType': 'BO', 'objectId': 1, 'objectName': '', 'units': 'no-units','required': 'YES', 'manuallyMapped': None, 'building': 'US-NYC-9TH', 'generalType': 'FCU','typeName': None,'assetName': 'AC-5-1', 'fullAssetPath': 'US-NYC-9TH:FCU:AC-5-1','standardFieldName': 'compressor_run_command'},
			{'location': '/One city block/111 8th/5th Floor', 'controlProgram': 'AC-5-1 (Mail Room)', 'name': 'Fan S/S', 'type': 'BMBO', 'path': '#1118th_ac-5-1/fan', 'deviceId': 2790529, 'objectType': 'BO', 'objectId': 0, 'objectName': ' ', 'units': 'no-units', 'required': 'YES', 'manuallyMapped': None, 'building': 'US-NYC-9TH', 'generalType': 'FCU', 'typeName': None, 'assetName': 'AC-5-1', 'fullAssetPath': 'US-NYC-9TH:FCU:AC-5-1', 'standardFieldName': 'discharge_fan_run_command'},
			{'location': '/One city block/111 8th/5th Floor', 'controlProgram': 'AC-5-1 (Mail Room)', 'name': 'Fan Status', 'type': 'BBV', 'path': '#1118th_ac-5-1/fan_status', 'deviceId': 300056, 'objectType': 'BV', 'objectId': 268, 'objectName': 'fan_status_28', 'units': 'no-units', 'required': 'YES', 'manuallyMapped': None, 'building': 'US-NYC-9TH', 'generalType': 'FCU', 'typeName': None, 'assetName': 'AC-5-1', 'fullAssetPath': 'US-NYC-9TH:FCU:AC-5-1', 'standardFieldName': 'discharge_fan_run_status'},
			{'location': '/One city block/111 8th/5th Floor', 'controlProgram': 'AC-5-1 (Mail Room)', 'name': 'Room Temp', 'type': 'BAV', 'path': '#1118th_ac-5-1/zone_temp', 'deviceId': 300056, 'objectType': 'AV', 'objectId': 627, 'objectName': 'zone_temp_28', 'units': 'degrees-fahrenheit', 'required': 'YES', 'manuallyMapped': None, 'building': 'US-NYC-9TH', 'generalType': 'FCU', 'typeName': None, 'assetName': 'AC-5-1', 'fullAssetPath': 'US-NYC-9TH:FCU:AC-5-1', 'standardFieldName': 'zone_air_temperature_sensor'},
			{'location': '/One city block/111 8th/5th Floor', 'controlProgram': 'AC-5-1 (Mail Room)', 'name': 'Occupied Setpoint', 'type': 'BMAV', 'path': '#1118th_ac-5-1/occ_setpt', 'deviceId': 2790529, 'objectType': 'AV', 'objectId': 90, 'objectName': ' ', 'units': 'degrees-fahrenheit', 'required': 'YES', 'manuallyMapped': None, 'building': 'US-NYC-9TH', 'generalType': 'FCU', 'typeName': None, 'assetName': 'AC-5-1', 'fullAssetPath': 'US-NYC-9TH:FCU:AC-5-1', 'standardFieldName': 'zone_air_cooling_temperature_sensor'},
			{'location': '/One city block/111 8th/10th Floor/AHU-10-1 & OAF-10-1', 'controlProgram': 'AHU-10-1', 'name': 'Total Cool Request', 'type': 'BAV', 'path': '#1118th_ahu_10_1/total_cl_req', 'deviceId': 303701, 'objectType': 'AV', 'objectId': 19, 'objectName': 'total_cl_req_1', 'units': 'no-units', 'required': 'YES', 'manuallyMapped': None, 'building': 'US-NYC-9TH', 'generalType': 'FCU', 'typeName': None, 'assetName': 'AHU-10-1', 'fullAssetPath': 'US-NYC-9TH:FCU:AHU-10-1', 'standardFieldName': 'cooling_request_count'},
			{'location': '/One city block/111 8th/10th Floor/AHU-10-1 & OAF-10-1', 'controlProgram': 'AHU-10-1', 'name': 'Total Zone Airflow', 'type': 'BAV', 'path': '#1118th_ahu_10_1/total_zone_flow', 'deviceId': 303701, 'objectType': 'AV', 'objectId': 21, 'objectName': 'total_zone_flow_1', 'units': 'cubic-feet-per-minute', 'required': 'YES', 'manuallyMapped': None, 'building': 'US-NYC-9TH', 'generalType': 'FCU', 'typeName': None, 'assetName': 'AHU-10-1', 'fullAssetPath': 'US-NYC-9TH:FCU:AHU-10-1', 'standardFieldName': 'supply_air_flowrate_sensor'},
			{'location': '/One city block/111 8th/10th Floor/AHU-10-1 & OAF-10-1', 'controlProgram': 'AHU-10-1', 'name': 'Total Airflow Requests', 'type': 'BAV', 'path': '#1118th_ahu_10_1/total_air_req', 'deviceId': 303701, 'objectType': 'AV', 'objectId': 18, 'objectName': 'total_air_req_1', 'units': 'no-units', 'required': 'YES', 'manuallyMapped': None, 'building': 'US-NYC-9TH', 'generalType': 'FCU', 'typeName': None, 'assetName': 'AHU-10-1', 'fullAssetPath': 'US-NYC-9TH:FCU:AHU-10-1', 'standardFieldName': 'pressurization_request_count'},
			{'location': '/One city block/111 8th/10th Floor/AHU-10-1 & OAF-10-1', 'controlProgram': 'AHU-10-1', 'name': 'Supply Fan Status', 'type': 'BBI', 'path': '#1118th_ahu_10_1/sf_status', 'deviceId': 303701, 'objectType': 'BI', 'objectId': 9, 'objectName': 'sf_status_1', 'units': 'no-units', 'required': 'YES', 'manuallyMapped': None, 'building': 'US-NYC-9TH', 'generalType': 'FCU', 'typeName': None, 'assetName': 'AHU-10-1', 'fullAssetPath': 'US-NYC-9TH:FCU:AHU-10-1', 'standardFieldName': 'supply_fan_run_status'},
			{'location': '/One city block/111 8th/10th Floor/AHU-10-1 & OAF-10-1', 'controlProgram': 'AHU-10-1 TPI', 'name': 'CW Temp', 'type': 'BAV', 'path': '#1118th_ahu-10-1_tpi/cwt', 'deviceId': 300084, 'objectType': 'AV', 'objectId': 20, 'objectName': 'cwt_2', 'units': 'degrees-fahrenheit', 'required': 'YES', 'manuallyMapped': None, 'building': 'US-NYC-9TH', 'generalType': 'FCU', 'typeName': None, 'assetName': 'AHU-10-1', 'fullAssetPath': 'US-NYC-9TH:FCU:AHU-10-1', 'standardFieldName': 'chilled_supply_water_temperature_sensor'}
		]

	assets = Assets()

	ont = ontology.ontology.Ontology()

	input_data = rows

	assets.load_from_data(input_data)
	fields = assets.get_all_asset_fields()

	assets.validate_without_errors(ont)
