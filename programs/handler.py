import os
import representations.representations
import ontology.ontology
import loadsheet.loadsheet as load
from pretty import PrettyPrint
import base64


def _convert_to_base64(data):
	"""
	Convert a data object into a base64 message.
	Used as a codeword to uniquely identify each asset type
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

def _print_type(type, type_dict):
	"""
	prints out a type's assets and fields
	"""
	print(f"ASSET GENERAL TYPE: {type}")
	print("--------------------------------------------------------------------------------")
	for field_hash in type_dict.keys():
		assets = type_dict[field_hash][0]
		fields = type_dict[field_hash][1]
		col_width = max(len(field) for field in fields) + 3

		print(f"ASSETS: {assets}\n")
		print("FIELDS")
		print("="*col_width)
		print("\n".join(fields))
		print("\n\n")

class Handler:
	"""
	Handler object for handling onboarding workflow.
	Acts as an interface between the CLI and the following libraries:
	 - representations: for converting the loadsheet into ontology-usable objects
	 - ontology: for asset validation and tMatching
	 - loadsheet: for loadsheet and bms imports and exports
	 			  as well as interaction with the rules engine
	"""
	def __init__(self):
		""" Initialize the handler. """
		# Create some flags to mark the status of the processes
		self.ontology_built = False
		self.representations_built = False
		self.loadsheet_built = False
		self.validated = False
		self.matched = False

		# Save some config info so that it can be reused
		self.last_loadsheet_path = ''
		self.last_rule_path = ''

# TODO: ask about build_ontology, import_loadsheet, validate_loadsheet, import_bms_data, apply_rules, import_excel redundancy
	def build_ontology(self, ontology_root):
		"""
		Try to build the ontology. If theres an error, print it out but don't blow up.
		args:
			- ontology_root: the root folder of the ontology to be imported

		returns: N/A
		"""
		try:
			# Adjust the resource directory in the ontology file to import from the desired location.
			# Build the ontology.
			ont = ontology.ontology.Ontology(ontology_root)
			ont.validate_without_errors()
			self.ontology_built = True
			self.ontology = ont
			print(f"[INFO]\tOntology built from '{ontology_root}'.")

		except Exception as e:
			# Raise the exception to the user
			print(f"[WARNING]\tOntology could not build: {e}")

	def import_loadsheet(self, loadsheet_path):
		"""
		Attempts to build loadsheet from given filepath
		If errors occur, prints them but doesn't close program

		args:
			- loadsheet_path: path of loadsheet Excel or BMS file

		returns: N/A
		"""
		# Check that the ontology is built first.
		#if not self.ontology_built:    #Ontology necessary for matching, not loadsheet
		#	print('[ERROR]\tOntology not built. Build it first.')
		#	return

		try:
			valid_file_types = {
				'.xlsx':'excel',
				'.csv':'bms_file'
			}
			file_type = os.path.splitext(loadsheet_path)[1]

			assert file_type in valid_file_types, f"Path '{loadsheet_path}' is not a valid file type (only .xlsx and .csv allowed)."
			assert os.path.exists(loadsheet_path), f"Loadsheet path '{loadsheet_path}' is not valid."
			try:
				# Import the data into the loadsheet object.
				self.loadsheet_built = True
				if valid_file_types[file_type] == 'bms_file':
					self.ls = load.Loadsheet.from_bms(loadsheet_path)
				elif valid_file_types[file_type] == 'excel':
					self.ls = load.Loadsheet.from_loadsheet(loadsheet_path)

				print("[INFO]\tLoadsheet Imported")

			except Exception as e:
				print("[ERROR]\tLoadsheet raised errors: {}".format(e))

		except Exception as e:
			print("[ERROR]\tCould not load: {}".format(e))

	def validate_loadsheet(self):
		""" Try to build the loadsheet. If theres an error, print it out but don't blow up. """

		# Check that the ontology is built first.
		if not self.ontology_built:
			print('[ERROR]\tOntology not built. Build it first.')
			return

		try:

			# Validate the loadsheet
			print('[INFO]\tValidating loadsheet.')
			self.ls.validate()
			print('[INFO]\tValidation complete, no errors.')

			try:
				# Convert the loadsheet to validation
				print('[INFO]\tConverting loadsheet into asset representations.')
				self.reps = representations.representations.Assets()
				self.reps.load_from_data(self.ls._data)
				print('[INFO]\tAsset representations built.')

				# Validate the representations
				print('[INFO]\tValidating assets.')
				self.reps.validate(self.ontology)
				print('[INFO]\tAsset representations validated!')
				self.representations_built = True

				print('[INFO]\tBuilding type representations...')
				self.general_types = self.reps.get_general_types()
				self.types = self.reps.determine_types()
				print(f'[INFO]\tType representations built: {len(self.general_types)} general types, {len(self.types)} unique types')
				self.validated = True

			except Exception as e:
				print(f"[ERROR]\tAsset represtations failed to build: {e}. ")

		except Exception as e:
			print(f"[ERROR]\tLoadsheet raised errors: {e}")

	def apply_rules(self,rules_path):     ####### REWRITE ME
		""" Run a given rules file over the loadsheet data. """

		#try:
		assert self.loadsheet_built, "Loadsheet is not initialized."
		assert os.path.exists(rules_path), f"Rule file path '{rules_path}' is not valid."
		print(f"[INFO]\tApplying rules from '{rules_path}'")
		self.ls.apply_rules(rules_path)
		print("[INFO]\tRules applied.")

		#except Exception as e:
		#	print(f"[ERROR]\tRules could not be applied: {e}.")

	def export_loadsheet(self,excel_path):
		"""
		exports loadshet data to excel file

		args:
			- excel_path: output filepath

		returns: N/A
		"""

		try:
			#Check that the loadsheet object is built.
			assert self.loadsheet_built, "Loadsheet is not initialized."
			folderpath = excel_path.replace(excel_path.split('/')[-1],'')
			assert os.path.exists(folderpath[:-1]), "Specified Excel path '{}' is not valid.".format(folderpath[:-1])
			print("[INFO]\tExporting to Excel file '{}'".format(excel_path))
			self.ls.export_to_loadsheet(excel_path)
			print("[INFO]\tData exported to Excel file!")

		except Exception as e:
			print('[ERROR]\tExcel file not exported: {}'.format(e))

	def import_excel(self,excel_path):
		""" Import from an Excel file. """
		#try:
			# Check that the loadsheet object is built.
		if not self.loadsheet_built:
			self.ls = loadsheet.loadsheet.Loadsheet()
			self.loadsheet_built = True

		if excel_path is None and self.last_loadsheet_path != '':
			excel_path = self.last_loadsheet_path
		assert os.path.exists(excel_path), "Specified Excel path '{}' is not valid.".format(excel_path)
		self.last_loadsheet_path = excel_path

		print("[INFO]\tImporting from Excel file '{}'".format(excel_path))
		self.ls.from_loadsheet(excel_path)

		#except Exception as e:
		#	print('[ERROR]\tExcel file not imported: {}'.format(e))

	def review_types(self,general_type=None):
		"""
		lets user review assets by generaltype

		args:
			- general_type: User can input type and see all assets of that type
						    Default None

		returns: N/A, prints review data to cmd
		"""
		if not self.validated:
			print("[ERROR]\tLoadsheet isn't validated yet... run 'validate' first.")
			return

		'''
		types is a dictionary of dictionary of list pairs
		each instance is of form
		"general_type":{
			"fields_hash":[[list_of asset paths],[list of type fields]],
			"fields_hash":[[list_of asset paths],[list of type fields]]
		}
		'''

		types = {}

		for asset_path in self.reps.assets:
			asset = self.reps.assets[asset_path]
			field_hash = _convert_to_base64(asset.get_fields())
			gT = asset.general_type
			if gT not in types.keys():
				types[gT] = {}
			if field_hash not in types[gT].keys():
				types[gT][field_hash] = [[],asset.get_fields()]
			types[gT][field_hash][0].append(asset.full_asset_name)

		#now we print
		if general_type is not None:
			relevant_assets = types[general_type]
			_print_type(general_type, relevant_assets)
		else:
			for type in types.keys():
				_print_type(type, types[type])

	def review_matches(self):
		"""
		reviews matches made once assets have been matched to the ontology
		match types are in {EXACT, CLOSE, INCOMPLETE, NONE}
		See match_types for more information

		args: N/A

		returns: N/A, but prints review to cmd
		"""
		if not self.matched:
			return

		matches = {}
		for asset_path in self.reps.assets:
			asset = self.reps.assets[asset_path]
			match = asset.match
			if match.match_type not in matches.keys():
				matches[match.match_type] = []
			matches[match.match_type].append(asset.full_asset_name)

		for match in matches:
			print(f"[{match}]: {matches[match]}")
			print('---------------------------------------------------------------------------------------------------------------------------------------------------\n\n')

	def match_types(self):
		"""
		Matches each asset to nearest asset in ontology

		prereqs:
			- loadsheet validation

		args: N/A

		returns: N/A
		"""

		if not self.validated:
			print("[ERROR]\tLoadsheet isn't validated yet... run 'validate' first.")
			return
		# Get matches for all types if the general_type specified is None.
		print("[INFO]\tMatching types to ontology...")

		for asset_path in self.reps.assets:
			asset = self.reps.assets[asset_path]
			match = self.ontology.find_best_fit_type(asset.get_fields(),'HVAC',asset.get_general_type())
			asset.add_match(match)

		self.matched = True

	def apply_matches(self):
		"""
		returns each asset, one at a time

		args: N/A
		returns: N/A
		"""
		for asset_path in self.reps.assets:
			yield self.reps.assets[asset_path]
