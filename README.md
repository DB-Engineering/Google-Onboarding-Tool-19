
# Onboarding Automation Tools
This repository hosts a set of libraries and command line tool for automating parts of the onboarding workflow.
It gives the user the ability to apply rule-based mapping automation, ingestion of multiple source files,
review loadsheet consistency, and validate entity definitions against a pre-defined ontology (i.e.,
Google's Digital Buildings Ontology).

## Repo Overview

This repo contains a few critical pieces:

1. A well defined ontology (`./ontology`)
2. A command line interface for dynamically building and checking loadsheets (`./programs/cli.py`)
3. Associated support libraries for the command line interface (and for future enhancement):
	1. An ontology validator
	2. A loadsheet validator
	3. A handler class that sits atop all the relevant classes
	4. A rules engine for applying regular expression pattern matching
	5. A representations class set for converting the loadsheet into ontology-usable objects

### Dependencies
This repo requires a few libraries be installed prior to use:
1. pyyaml (for parsing YAML documents)
2. pyfiglet (for fancy CLI name)
3. openpyxl (for Excel read/write)
4. pandas (for loadsheet backend)
5. ruamel.yaml

If not installed, setup libraries by running `setup.py` in your command line:

```>>> python setup.py```


## Example Workflow
**Start the Commmand Line Interface (LoadBoy2000):**
1. Run the progam:
	`>>> python cli.py`

**Loadsheet process:**
1. Prepare the loadsheet
	1. Get point list (in XSLX or CSV format)
	2. Put it in the loadsheet template sheet
	3. Run the RULE ENGINE over the data
	4. Manually review the unmapped points
	
2. Validate the loadsheet
3. Match to existing DBO types
4. Create new types, as needed
5. Apply types to the loadsheet

**Example workflow:**
1. Import the ontology:

	`>>> import ontology '../ontology/yaml/resources'`
	If successful, you should get CLI confirmation.

	Manual (optional) unit tests:
	- Add a fake field to the field list ('bacon_sensor') -- should return error
	- Add a fake field with valid subfields ('supply_sensor') -- will NOT return an error.
	- Add a new type with a fake field -- should return error
	- Add duplicate fields to fake type -- should return error

2. Clean raw loadsheet:

	`>>> clean '../loadsheet/Loadsheet_ALC.xlsx'`

3. Import the cleaned loadsheet:

	`>>> import loadsheet '../loadsheet/Loadsheet_ALC.xlsx'`
	
	If successful, you should get CLI confirmation.

4. Normalize the loadsheet (AKA apply the ruleset):

	`>>> normalize '../resources/rules/google_rules.json'`
	
	If successful, you should get CLI confirmation.

5. Export to a new loadsheet for review:

	`>>> export excel '../loadsheet/Loadsheet_ALC_Normalized.xlsx'`

	Rules should have been applied. You should see a new file with normalized columns (e.g., `required`, `assetName`, and `standardFieldName`) filled in. 

6. Perform a manual review and repeat steps 3, 4, and 5 as necessary.

7. Import and validate finished loadsheet:

	`>>> import loadsheet '../loadsheet/Loadsheet_ALC_Final.xlsx'`
	
	`>>> validate`

	Validation will fail for common errors:
	- duplicate `standardFieldName` and `fullAssetPath` combinations
	- an invalid `standardFieldName` (i.e., not defined in the referenced ontology or mispelled)
	- missing bacnet info (e.g., missing `objectId`)

8. When no validation errors are present, assets in the loadsheet can be matched to DBO entity types:

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

11. Convert normalized loadsheet to ABEL spreadsheet:

	`>>> convert abel ./path/to/building/payload.csv`


## Known deficiencies and future development

The following is a list of issues that need to be addressed before widespread use:
	- Add rigorous typing to all methods
	- make the necessary fields in handler and representations private
