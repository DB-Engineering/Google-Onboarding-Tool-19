import cmd
import handler
import os
import ontology.ontology
from pyfiglet import Figlet
from pretty import PrettyPrint

"""

TODO: Fix path inputs to recognize quotes.

Workflow:
0. Build the types for assignment
1. For each type in the types.
	a. If the type match is exact, just assign it automatically.
	b. If the type is not an exact match, make a choice:
		i. Skip the type (i.e. dont assign it anything)
		ii. Assign suggested type.
		iii. Assign a different, user-entered type.
			x. Validate that it exists.
"""

class Mapper(cmd.Cmd):
	""" Mapper class to supervise the workflow for """

	def __init__(self):
		super(Mapper, self).__init__()

		self.handler = handler.Handler()
		self._clear()
		f = Figlet()
		intro_text = """============================================\n"""
		intro_text += """Welcome to the Loadsheet Builder. \n"""
		intro_text += """Use this tool to build and review loadsheets. \n"""
		intro_text += """For help with functions, type 'help' or view README. \n"""
		intro_text += """============================================"""
		self.intro = f.renderText('LoadBoy2000')+intro_text

		self.prompt = '>>> '

	def _parse_args(self,raw_args):
		""" Parses raw arguments into individual arguments. Useful for dealing
		with file paths, where there may be spaces and thus require quoting."""

		import re
		regex = re.compile(r'''
			'.*?' | # single quoted substring
			".*?" | # double quoted substring
			\S+ # all the rest
			''', re.VERBOSE)

		raw_matches = regex.findall(raw_args)
		matches = [match.replace('"','').replace("'","") for match in raw_matches]

		return matches

	def _clear(self):
		""" Clear the current console."""
		os.system('cls' if os.name == 'nt' else 'clear')

	"""Both quit and exit quit the application"""
	def do_quit(self,args):
		""" Quits LoadBoy """
		return True
	def do_exit(self, args):
		""" Exits LoadBoy """
		return True

	def do_clear(self,args):
		""" Clear the current console. """
		self._clear()
		print(self.intro)

	def do_import(self,args):
		"""			Facilitate the importing of data.
			usage: import <bms|loadsheet|ontology> <file|folder> """

		# Check that the right number of arguments are supplied.
		inputs = self._parse_args(args)
		for arg in inputs: print(arg)

		if len(inputs) != 2:
			print("[ERROR]\tNot the correct number of arguments. See help for details on import function.")
			return

		import_type = inputs[0]
		path = inputs[1]

		valid_first_arg = ['bms','loadsheet','ontology']

		# Check that the first argument is a valid import argument.
		if inputs[0] not in valid_first_arg:
			print("[ERROR]\t'{}'' not a valid input. Valid inputs are {}".format(inputs[1],valid_first_arg))
			return

		if import_type == 'bms':
			print("[INFO]\tImporting from BMS file...")
			self.handler.import_loadsheet(path)

		if import_type == 'loadsheet':
			print("[INFO]\tImporting from loadsheet...")
			self.handler.import_loadsheet(path)

		if import_type == 'ontology':
			print("[INFO]\tImporting ontology...")
			self.handler.build_ontology(path)

	def do_normalize(self,args):
		"""			Run the rules file given a specific rules filepath
			usage: normalize <rules filepath>"""

		inputs = self._parse_args(args)

		if len(inputs) != 1:
			print("[ERROR]\tOnly one argument is accepted; {} were passed.".format(len(inputs)))
			return

		print("[INFO]\tApplying rules...")
		self.handler.apply_rules(inputs[0])

	def do_export(self,args):
		"""			Export the data as an excel file.
			usage: export <excel> <export filepath>"""

		# Check that the right number of arguments are supplied.
		inputs = self._parse_args(args)
		if len(inputs) != 2:
			print("[ERROR]\tNot the correct number of arguments. See help for details on export function.")
			return

		export_type = inputs[0]
		path = inputs[1]

		valid_first_arg = ['excel']

		# Check that the first argument is a valid import argument.
		if inputs[0] not in valid_first_arg:
			print("[ERROR]\t'{}'' not a valid input. Valid inputs are {}".format(inputs[1],valid_first_arg))
			return

		if export_type == 'excel':
			print("[INFO]\tExporting to Excel loadsheet.")
			self.handler.export_loadsheet(path)

	def do_validate(self,args):
		"""			Validate the loadsheet data against the ontology.
			usage: validate"""

		self.handler.validate_loadsheet()

	def do_review(self, args):
		"""			Review GeneralTypes and Matches. Loadsheet must be validated
			usage: review <optional generalType> """

		if not self.handler.validated:
			print("[ERROR]\tLoadsheet isn't validated yet. Run 'validate' first.")
			return


		inputs = args.split()

		if len(inputs) > 1:
			print("[ERROR]\tNot the correct number of arguments. See help for details on review function.")
			return

		generalType = None
		if len(inputs) > 0:
			generalType = inputs[1]


		self.handler.review_types(generalType)

	def do_match(self, args):
		"""			Match the types to their nearest types.
			usage: match """

		#if not self.handler.validated:
			#print("[ERROR]\tLoadsheet not validated. Run 'validate' before matching or reviewing.")
			#return

		self.handler.match_types()
		print("[INFO]\tType matches added. Use 'review' to see outputs.")

	def do_apply(self, args):
		"""			Apply the types one at a time.
			Apply all to review all matches
			Apply close to review inexact matches
			while applying, Exit to exit apply loop
			usage: apply <all/close>"""

		inputs = args.split()
		if len(inputs) != 1:
			print("[ERROR]\tIncorrect number of inputs. See 'help' for more information on this function.")
			return

		if not self.handler.matched:
			print("[ERROR]\tMatches not performed. Run 'match' first.")
			return

		question_types = ["INCOMPLETE"] #The types of match where we ask if apply or skip
		if inputs[0] == "all":
			question_types.append("EXACT")
		# TODO: see if anyone can figure out how to move this to backend
		for asset in self.handler.apply_matches():
			match_type = asset.match.match_type
			if match_type in question_types:
				print(f"ASSET NAME: {asset.full_asset_name}")
				asset.match.print_comparison()
				action = self._ask("   >>> Apply or Skip this Match? ", ["Apply", "Skip", "Exit"]).lower()
				if action == 'apply':
					asset.apply_match()
				elif action == 'skip':
					continue
				elif action == 'exit':
					break
			elif match_type == "EXACT":
				asset.apply_match()
			else:
				asset.match.print_comparison()
				a = input("   >>> Functionality not yet added, press enter to continue")

		print("[INFO]\tAll type matches applied. Use 'export' to export finished loadsheet.")

		self.handler.ls._data = self.handler.reps.dump_to_data()

	#input validator. returns one of the inputs, whichever the user gives
	def _ask(self, qn, answers=["yes", "no"]):
		inp = input(qn).lower()
		answers_lower = [a.lower() for a in answers]
		valid_answers = "Valid Responses are: " + ', '.join(answers)
		while inp not in answers_lower:
			print(valid_answers)
			inp = input(qn)
		return inp



if __name__ == '__main__':
	con = Mapper()
	con.cmdloop()
