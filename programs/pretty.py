#Copyright 2020 DB Engineering

#This file is part of OnboardingTool

#OnboardingTool is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.

#Foobar is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.

#You should have received a copy of the GNU General Public License
#along with OnboardingTool.  If not, see https://www.gnu.org/licenses/.

""" Helper functions for prettifying outputs. """

import json

def PrettyPrint(obj):
	""" Pretty print the input dictionary. """
	print(json.dumps(obj,sort_keys=True,indent=2))
