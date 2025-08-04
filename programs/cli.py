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
        self.do_clear(None)
        f = Figlet()
        intro_text = """============================================\n"""
        intro_text += """Welcome to the Loadsheet Builder. \n"""
        intro_text += """Use this tool to build and review loadsheets. \n"""
        intro_text += """For help with functions, type 'help' or view README. \n"""
        intro_text += """OnboardingTool Copyright (C) 2020 DB Engineering"""
        intro_text += """To view license information, type 'license'\n"""
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

    def do_apply(self, args):
        """
        Apply the types one at a time.
        Apply all to review all matches
        Apply close to review inexact matches
        while applying, Exit to exit apply loop
        Usage: apply <all/close>
        """

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
            self.do_clear(None)
            match_type = asset.match.match_type
            print("\n")
            print(f"ASSET NAME: {asset.full_asset_name}")
            print(f"ASSET TYPE: {asset.general_type}")
            if match_type in question_types:
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
    
    def do_convert(self, args):
        """
        Converts current loadsheet into ABEL sheet.
        Usage: convert abel
        """
        inputs = self._parse_args(args)
        valid_first_arg = ['abel']
        if inputs[0] not in valid_first_arg:
            print("[ERROR]\t'{}'' not a valid input. Valid inputs are {}".format(inputs[1],valid_first_arg))
        elif not (self.handler.payload_path or self.handler.last_loadsheet_path):
            print("[ERROR]\t Payload and valid loadsheet must be imported before export an ABEL spreadsheet.")
        else:
            try: 
                if len(inputs) == 2:
                    self.handler.export_abel_spreadsheet(excel_path=self.handler.last_loadsheet_path, payload_path=self.handler.payload_path, output_path=inputs[1])
                else:
                    self.handler.export_abel_spreadsheet(excel_path=self.handler.last_loadsheet_path, payload_path=self.handler.payload_path)
            except Exception as e:
                print(f"[ERROR]\t Could not convert loadsheet: {e}.")

    def do_export(self, args):
        """			
        Export the data as an excel file.
        Usage: export excel <export filepath>
        """

        # Check that the right number of arguments are supplied.
        inputs = self._parse_args(args)
        if len(inputs) != 2:
            print("[ERROR]\tNot the correct number of arguments. See help for details on export function.")
            return

        export_type = inputs[0]
        export_path = inputs[1]
        valid_first_arg = ['excel']

        # Check that the first argument is a valid import argument.
        if inputs[0] not in valid_first_arg:
            print("[ERROR]\t'{}'' not a valid input. Valid inputs are {}".format(inputs[1],valid_first_arg))
            return

        if export_type == 'excel':
            self.handler.export_loadsheet(excel_path=export_path)
    
    def do_import(self, args):
        """			
        Facilitate the importing of data.
        Usage: import <bms|loadsheet|ontology> <file|folder>
        """

        # Check that the right number of arguments are supplied.
        inputs = self._parse_args(args)

        if len(inputs) != 2:
            print("[ERROR]\tNot the correct number of arguments. See help for details on import function.")
            return

        import_type = inputs[0]
        path = inputs[1]

        valid_first_arg = ['bms','loadsheet','ontology', 'payload', 'bc']

        # Check that the first argument is a valid import argument.
        if inputs[0] not in valid_first_arg:
            print("[ERROR]\t'{}'' not a valid input. Valid inputs are {}".format(inputs[1],valid_first_arg))
            return

        # 01132021: why was this using the from_loadsheet import method?
        # if import_type == 'bms':
        # 	print("[INFO]\tImporting from BMS file...")
        # 	self.handler.import_loadsheet(path, has_normalized_fields=False)

        # changed call here and created import_bms method in handler
        # to address this error; not a permanent fix..
        if import_type == 'bms':
            print("[INFO]\tImporting from BMS file...")
            self.handler.import_bms(path, has_normalized_fields=False)
        # end by sypks

        elif import_type == 'loadsheet':
            print("[INFO]\tImporting from loadsheet...")
            self.handler.import_loadsheet(path, has_normalized_fields=True)

        elif import_type == 'ontology':
            print("[INFO]\tImporting ontology...")
            self.handler.build_ontology(path)

        elif import_type == 'payload':
            print("[INFO]\tImporting payload...")
            self.handler.payload_path = path
            print("[INFO]\tPayload imported.")
    
    def do_match(self, _):
        """			
        Match the types to their nearest types.
        Usage: match
        """

        #if not self.handler.validated:
            #print("[ERROR]\tLoadsheet not validated. Run 'validate' before matching or reviewing.")
            #return

        self.handler.match_types()
        print("[INFO]\tType matches added. Use 'review' to see outputs.")
    
    def do_normalize(self, args):
        """			
        Run the rules file given a specific rules filepath
        Usage: normalize <rules filepath>
        """

        inputs = self._parse_args(args)

        if len(inputs) != 1:
            print("[ERROR]\tOnly one argument is accepted; {} were passed.".format(len(inputs)))
            return

        print("[INFO]\tApplying rules...")
        self.handler.apply_rules(inputs[0])
    
    def do_review(self, args):
        """			
        Review GeneralTypes and Matches. Loadsheet must be validated
        Usage: review <optional generalType>
        """

        if not self.handler.validated:
            print("[ERROR]\tLoadsheet isn't validated yet. Run 'validate' first.")
            return

        inputs = args.split()

        if len(inputs) > 1:
            print("[ERROR]\tNot the correct number of arguments. See help for details on review function.")
            return

        generalType = None
        if len(inputs) > 0:
            generalType = inputs[0]


        self.handler.review_types(generalType)
    
    def do_clear(self, _):
        """
        Clears the current console.
        Usage: clear
        """
        os.system('cls' if os.name == 'nt' else 'clear')
        print(self.intro)

    def do_license(self, _):
        """	
        Show Apache License
        Usage: license
        """

        l = "Copyright 2020 DB Engineering\n\n"
        l += 'Licensed under the Apache License, Version 2.0 (the "License");\n'
        l += "you may not use this file except in compliance with the License\n"
        l += "You may obtain a copy of the License at\n"
        l += "    http://www.apache.org/licenses/LICENSE-2.0\n"
        l += "Unless required by applicable law or agreed to in writing, software\n"
        l += 'distributed under the License is distributed on an "AS IS" BASIS,\n'
        l += "WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.\n"
        l += "See the License for the specific language governing permissions and\n"
        l += "limitations under the License.\n"

        print(l)
    
    def do_ml_normalize(self, _):
        """			
        Run the rules file given a specific rules filepath
        Usage: normalize <rules filepath>
        """

        print("[INFO]\tNormalizing...")
        self.handler.apply_ml_normalization()

    def do_quit(self, _):
        """
        Quits LoadBoy
        Usage: quit
        """
        return True
    
    # def do_validate(self, _):   # This should be removed once the "do_loadsheet_checks" function is completed
    #     """			
    #     Validate the loadsheet data against the ontology.
    #     Usage: validate
    #     """

    #     self.handler.validate_loadsheet()

    def do_loadsheet_checks(self, _): 
        """			
        Run a series of validation checks on the loadsheet
        Usage: loadsheet_checks
        """
        self.handler.loadsheet_checks()     
    
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