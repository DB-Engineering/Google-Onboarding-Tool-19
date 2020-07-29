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

"""
Rule Library

Provides a framework for parsing message to determine key characteristics, based on the
content of the message. A rule consists of several basic components:

	1. 	Filter: a series of filters that allow the rule to be applied. Prevents the rule from being
		misapplied to something not meant for it.
	2. 	Rule: the principal concern for the rule; its findings can be used for the output.
	3. 	Output: The output to the object based on the finding of the rule. Can include things like
		capture groups, set strings, anything (TODO: anything other than capture groups and strings).
"""

import logging
import csv, json, re, datetime, os
import math


class Rule:
	""" Creates a rule object, which can be applied to a JSON object for 'normalizing' it. """

	def __init__(self,ruleJson,caseSensitive=True):
		""" Get the rule going. Instantiate the data from the rule
		as class variables and put it in the right format. Also
		start the log file for the job. This will help debug rules
		that overwrite other rules or missed rows.

		args:
			- ruleJson: dictionary read-in of the rules file to turn into Rules
			- caseSensitive: flag of whether or not the filters patterns should be case-caseSensitive
							 defaults True

		"""
		assert caseSensitive in (True,False), "Not a valid case sensitivity flag (only True or False)"
		self.caseSensitive = caseSensitive
		self.ruleName = ruleJson['ruleName']
		#print(self.ruleName)
		self.ruleField = ruleJson['ruleField']
		if type(ruleJson['rulePattern']) is list:
			self.rulePattern = ruleJson['rulePattern']
		else:
			if self.caseSensitive:
				self.rulePattern = re.compile(ruleJson.get('rulePattern',''))
			else:
				self.rulePattern = re.compile(ruleJson.get('rulePattern',''),re.IGNORECASE)

		self.outputs = ruleJson['outputs']

		if 'filters' in ruleJson:
			self.filters = ruleJson['filters']
			self.filterField = [key for key in self.filters]
			self.filterType = [self.filters[key][0] for key in self.filterField]
			for fT in self.filterType:
				assert fT in ['exclude','include'], 'Not a valid filter!'
			if self.caseSensitive:
				self.filterPattern = [re.compile(self.filters[key][1]) for key in self.filterField]
			else:
				self.filterPattern = [re.compile(self.filters[key][1],re.IGNORECASE) for key in self.filterField]

		else:
			self.filterField = []
			self.filterType = []
			self.filterPattern = []

		# Create a log list for the application of the rule.
		self.log = []

	def _ResetMsg(self):
		""" Reset the logging messages. """
		self.log = []

	def Apply(self,dataJson):
		"""
		Apply the whole chain of rule components to the passed data dictionary.

		args:
			- dataJson: loadsheet data in the dictionary of lists format
		"""
		self.log.append(f'[INFO] Applying Rule "{self.ruleName}"')
		self._ResetMsg()
		self.ApplyFilter(dataJson)
		#[print(msg) for msg in self.log] #Note: replacing print to command with printing everything to a log

	def ApplyFilter(self,dataJson):
		""" Determine if the filter applies. If it does keep going.
		Log the filter details (whether there is one to apply)

		args:
			- dataJson: the data we're running the filters over
		"""

		for fF, fP, fT in zip(self.filterField,self.filterPattern,self.filterType):
			# Check if the field is not in the JSON (warn out)
			if fF not in dataJson:
				ismatch = False
				self.log.append(f'[WARN] Filter field ({fF}) not in message.')
				return
			else:
				if dataJson[fF] is None or dataJson[fF] != dataJson[fF]:
					#to catch NaN, we check if dataJson[fF] equals itself
					### None space change made by akoltko 20200716
					dataJson[fF] = ''
				ismatch = bool(fP.search(dataJson[fF]))
				self.log.append(f'[INFO] Filter field ({fF}) with pattern  ({fP}) and type ({fT}): {ismatch}')
			isinclude = fT =='include'

			if ismatch != isinclude:
				self.log.append(f'[INFO] Filter "{fP}" [{fT}] applied to "{dataJson[fF]}" ({fF}): NOT MATCHED.')
				return
			else:
				self.log.append(f'[INFO] Filter "{fP}" [{fT}] applied to "{dataJson[fF]}" ({fF}): MATCHED.')
		else:
			self.ApplyRule(dataJson)

	def ApplyRule(self,dataJson):
		"""
		Apply the rule to the data row. If matches, outputs.

		args:
			- dataJson: dictionary of lists of the row we're applying the rule to
		"""
		#print('\tApplying Rule')
		if type(self.rulePattern) is list:
			if dataJson[self.ruleField] in self.rulePattern:
				self.log.append(f'[INFO] Rule "{str(self.rulePattern)}" applied to "{self.ruleField}" ({dataJson[self.ruleField]}): MATCHED')
				#self.ruleMsg = '"'+self.ruleName + '" applied to [' + self.ruleField + '] ("' + dataJson[self.ruleField] + '"")'
				self.ApplyOutputs(dataJson)
			else:
				self.log.append(f'[INFO] Rule "{self.rulePattern}" applied to "{self.ruleField}" ({dataJson[self.ruleField]}): NOT MATCHED')
		else:
			# If the rule field doesnt have a value, throw it away.
			if dataJson[self.ruleField] is None or dataJson[self.ruleField] != dataJson[self.ruleField]:
				### None space change made by akoltko 20200716
				dataJson[self.ruleField] = ''

			matches = self.rulePattern.search(str(dataJson[self.ruleField]))

			if matches:
				self.log.append(f'[INFO] Rule "{self.rulePattern}" applied to "{self.ruleField}" ({dataJson[self.ruleField]}): MATCHED')
				self.ApplyOutputs(dataJson,matches)
			else:
				self.log.append(f'[INFO] Rule "{self.rulePattern}" applied to "{self.ruleField}" ({dataJson[self.ruleField]}): NOT MATCHED')

	def ApplyOutputs(self,dataJson,matches=None):
		"""
		Apply the outputs to the data row. If no matches are provided its assumed from a list match.

		args:
			- dataJson: the row of data we're applying the outputs to
			- matches: what matches were made, for dynamic outputs, default None
		"""
		warnFlag = False
		if matches == None:
			for key in self.outputs:
				if key in dataJson:
					if dataJson[key] is not None:
						warnFlag = True
						currentVal = dataJson[key]
						overVal = self.outputs[key]
				else:
					self.log.append(f'[INFO] Output "{dataJson[key]}" ({key}) set.')
				dataJson[key] = self.outputs[key]
				self.log.append(f'[INFO] Output "{dataJson[key]}" ({key}) set.')
		else:
			for key in self.outputs:
				if key in dataJson:
					if dataJson[key] is not None:
						warnFlag = True
				if type(self.outputs[key]) is int:
					dataJson[key] = matches.group(self.outputs[key])
					self.log.append(f'[INFO] Output "{dataJson[key]}" ({key}) set.')
				elif type(self.outputs[key]) is list:
					outStr = ''
					for elem in self.outputs[key]:
						if type(elem) is str:
							outStr += elem
						elif type(elem) is int:
							outStr += matches.group(elem)
					dataJson[key] = outStr
				else:
					dataJson[key] = self.outputs[key]
					self.log.append(f'[INFO] Output "{dataJson[key]}" ({key}) set.')
		if warnFlag == False:
			self.log.append('[INFO] Full rule applied.')

		else:
			self.log.append('[WARN] Full rule applied (Output Overwritten)' )

	def _SaveLog(self):
		name = "../Logs/rule_log_" + str(datetime.datetime.now()).replace(" ","_").replace(":", "-") + ".txt"
		with open(name, 'w') as logfile:
			[logfile.write(l + '\n') for l in self.log]

class Rules:
	""" Class used for handling all rules in a set. Records rule application for troubleshooting. """

	def __init__(self,rulesFile=None, rulesJson=None, caseSensitive=True):
		"""
		set of individual rule objects, created from filepath or existing json

		args:
			- rulesFile: a filepath to import rules from, default none
			- rulesJson: a dictionary of lists making up a set of rules, default None
			- caseSensitive: flag for using regex as caseSensitive or not, default True


		"""
		self.caseSensitive = caseSensitive
		if rulesFile is not None:
			rules = json.load(open(rulesFile,'r'))
		elif rulesJson is not None:
			rules=rulesJson
		else:
			assert False, "No ruleset given"
		self.ruleSet = 	[Rule(r, caseSensitive=self.caseSensitive) for r in rules['rules']]
		self.ruleCount = len(self.ruleSet)								#TODO: Why is this here?
		self.msg = []
		self._ResetMsg()

	def _ResetMsg(self):
		""" Clear the message log. """
		self.msg.append('''================ RULE LOG ================''')

	def ApplyRules(self,dataJson):
		"""
		Apply all rules from the file to a given JSON object.

		args:
			- dataJson: the data to apply rules to
		"""
		#self._ResetMsg()
		for rule in self.ruleSet:
			rule.Apply(dataJson)
			self.msg.append('[INFO] Rule: {}'.format(rule.ruleName))
			self.msg.append('[INFO] Data input: {}'.format(str(dataJson)))
			self.msg += rule.log

	#severities are INFO, WARN, or ERROR
	#ERROR>WARN>INFO
	def PrintLog(self, min_severity="WARN"):
		"""
		prints all log messages to command line
		"""
		if min_severity=="INFO":
			[print(m) for m in self.msg]
		elif min_severity=="WARN":
			[print(m) for m in self.msg if "INFO" not in m]
		elif min_severity == "ERROR":
			[print(m) for m in self.msg if "ERROR" in m]


	def SaveLog(self):
		"""
		saves all log messages to preset text file location
		"""
		name = "../Logs/ruleset_log_" +\
		       str(datetime.datetime.now()).replace(" ","_").replace(":", "-") +\
			   ".txt"
		with open(name, 'w') as lf:
			if min_severity=="INFO":
				[lf.write(m) for m in self.msg]
			elif min_severity=="WARN":
				[lf.write(m) for m in self.msg if "INFO" not in m]
			elif min_severity == "ERROR":
				[lf.write(m) for m in self.msg if "ERROR" in m]



if __name__ == '__main__':
	# Example code block.
	row = json.load(open('../RawData/testData.json','r'))
	print(row)
	r = Rules('../Rules/testRules.json')
	r.ApplyRules(row)
	r.PrintLog('INFO')
