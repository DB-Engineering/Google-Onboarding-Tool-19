""" Helper functions for prettifying outputs. """

import json

def PrettyPrint(obj):
	""" Pretty print the input dictionary. """ 
	print(json.dumps(obj,sort_keys=True,indent=2))


