
# Onboarding Automation Tools
This repository hosts a set of libraries and command line tool for automating parts of the onboarding workflow.
It gives the user the ability to apply rule-based mapping automation, ingestion of multiple source files,
review loadsheet consistency, and validate entity definitions against a pre-defined ontology (consistent with
Google's Digital Facilities).

## Repo Overview

### Dependencies
This repo requires a few libraries be installed prior to use:
1. pyyaml (for parsing YAML documents)
2. pyfiglet (for fancy CLI name)
3. openpyxl (for Excel read/write)
4. pandas (for loadsheet backend)
5. typing (for type checking)

If not installed, setup libraries using

```python setup.py```

This repo contains a few critical pieces:

1. A well defined ontology (`./ontology`)
2. A command line interface for dynamically building and checking loadsheets (`./programs/cli.py`)
3. Associated support libraries for the command line interface (and for future enhancement):
	1. An ontology validator
	2. A loadsheet validator
	3. A handler class that sits atop all the relevant classes
	4. A rules engine for applying regular expression pattern matching.
	5. A representations class set for converting the loadsheet into ontology-usable objects


## Example Workflow


**Loadsheet process:**
1. Prepare the loadsheet

	a. Get point list
	
	b. Put it in the loadsheet template sheet
	
	c. Run the RULE ENGINE over the data
	
	d. Manually review the unmapped points
	
2. Validate the loadsheet
3. Create necessary types


**Example workflow:**
1. Import the ontology:

	`>>> import ontology '../ontology/yaml/resources'`

	Should run without error.
	
	Add a fake field to the field list ('bacon_sensor') -- should return error
	
	Add a fake field with valid subfields ('supply_sensor') -- will NOT return an error.
	
	Add a new type with a fake field -- should return error
	
	Add duplicate fields to fake type -- should return error

2. Clean loadsheet for import:

	`>>> clean ./path/to/raw/loadsheet.xlsx`

3. Import the raw loadsheet:

	`>>> import loadsheet '../loadsheet/Loadsheet_ALC.xlsx'`

	Should get CLI confirmation

4. Normalize the loadsheet:

	`>>> normalize '../resources/rules/google_rules.json'`

	Should get CLI confirmation

5. Export to a new loadsheet for review:

	`>>> export excel '../loadsheet/Loadsheet_ALC_Normalized.xlsx'`

	Should see a new file with normalized fields filled in.
	Rules should have been applied.

6. Perform a manual review and repeat steps 2, 3, and 4 as necessary.

7. Import and validate finished loadsheet:

	`>>> import loadsheet '../loadsheet/Loadsheet_ALC_Final.xlsx'
	
	`>>> validate`

	Should run without errors

	Mess with the loadsheet to show how validation works for the following:
	- an invalid standard field name
	- missing bacnet info

8. When no validation errors are issued, types can be matched:

	`>>> match`

9. Perform a review of type matches and assign to a valid canonical type.

	`>>> review generalTypes`
	`>>> review generalTypes VAV`
	`>>> review generalTypes VAV 1`

	or

	`>>> review matches`


10. Apply the matched types
	Either review all matches made using

	`>>> apply all`

	Or Autoapply exact matches and only review inexact using

	`>>> apply close`

11. Convert normalized loadsheet to ABEL spreadsheet

	`>>> convert abel ./path/to/building/payload.csv`


## Known Issues and Future Development

The following is a list of issues that need to be addressed before widespread use:
	- Add rigorous typing to all methods
	- make the necessary fields in handler and representations private
