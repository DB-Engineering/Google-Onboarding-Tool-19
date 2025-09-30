
# Onboarding Automation Tools
This repository hosts a set of libraries and command line tool for automating parts of the onboarding workflow.
It gives the user the ability to apply rule-based mapping automation, ingest multiple source files,
review loadsheet consistency, and validate entity definitions against a pre-defined ontology (i.e.,
Google's [Digital Buildings Ontology](https://github.com/google/digitalbuildings)).

## Table of Contents
- [Repo Overview](#repo-overview)
- [Dependencies](#dependencies)
- [Workflow](#workflow)
    - [Detailed Workflow](#detailed-workflow)
- [Known Deficiencies and Future Development](#known-deficiencies-and-future-development)
- [Optional Unit Tests](#optional-unit-tests)

## Repo Overview

This repo contains the following critical pieces:
1. A well defined ontology (`./ontology`)
2. A command line interface for dynamically building and checking loadsheets (`./programs/cli.py`)
3. Associated support libraries for the command line interface (and for future enhancement):
	1. An ontology validator
	2. A loadsheet validator
	3. A handler class that sits atop all the relevant classes
	4. A rules engine for applying regular expression pattern matching
	5. A representations class set for converting the loadsheet into ontology-usable objects

### Requirements
For complete functionality the tool requires python 3.11 or 3.12.

### Setup
From your command prompt (or euivalent console) run the progam (note that `python` is used here, but your local machine may use `py`, `py3`, or `python3`).

Windows:
```
python -3.11 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Linux:
```
python -3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```


## Workflow
**General Loadsheet Process**
1. Prepare the loadsheet
	1. Obtain a point list (in XSLX or CSV format)
	2. Format the point list to adhere to the loadsheet template sheet
	3. Run the rule engine over the data
	4. Manually review the unmapped points
2. Validate the loadsheet
3. Match the entities in the loadsheet to existing DBO types
4. Create new types in the referenced ontology, as needed
5. Apply matched DBO types to the loadsheet

### Detailed Workflow
#### Step 1 - Start the Commmand Line Interface (LoadBoy2000)
From your command prompt (or euivalent console) run the progam (note that `python` is used here, but your local machine may use `py`, `py3`, or `python3`).

```
python cli.py
```

#### Step 2 - Import the ontology
Once the LoadBoy2000 program starts, pass in a path (absolute or relative) to the ontology that the program will reference during validation and type matching. If successful, you should get CLI confirmation.

```
import ontology '../ontology/yaml/resources'
````

#### [Optional] Step 3 - Import raw BMS loadsheet
This step is only required if you are passing in a raw points list (directly exported from an ALC BMS).
```
import bms '../loadsheet/Loadsheet_ALC.csv'
```

#### Step 4 - Import the loadsheet (either the "clean" output from Step 3 or a previously "cleaned" loadsheet)
Load the loadsheet that you want to validate, normalized, and type match. If successful, you should get CLI confirmation.
```
import loadsheet '../loadsheet/Loadsheet_ALC.xlsx'
```

#### Step 5.1 - Normalize the loadsheet using ML models:
Apply ML models combined with rules to predict required, standardFieldName, assetName, generalType, units. If successful, you should get CLI confirmation.

```
ml_normalize
```

#### Step 5.2 - OR Normalize the loadsheet using legacy rule-based approach:
Apply regular expression rules to populate the standardFieldName column. The default ruleset uses DBO field names. If successful, you should get CLI confirmation.

```
normalize '../resources/rules/google_rules.json'
```
	

#### Step 6 - Export to a NEW loadsheet for review
Once rules are successfully applied, you should see a new file with normalized columns (e.g., `required`, `assetName`, and `standardFieldName`) filled in. 
Tool adds a Pivot table.

```
export excel '../loadsheet/Loadsheet_ALC_Normalized.xlsx'
```


#### Step 7 - Perform a manual review and repeat steps 3, 4, and 5 as necessary.
Perform a manual review to ensure that the applied standardFieldNames are correct. Correct any incorrect field names, remove any field names that are not relevant to the model (e.g., PID inputs) by marking the `reqired` column as "NO", and add any field names that were not populated but are relevant to the model by marking the `required` column as "YES".

#### Step 8 - Import and validate the loadsheet
Import the loadsheet (after manual review from Step 7) that has the standardFieldName column populated for fields of interest.
```
import loadsheet '../loadsheet/Loadsheet_ALC_Final.xlsx'
```

Run validation over the loadsheet
```
validate
```

Validation will fail for common errors:
- Duplicate `standardFieldName` and `assetName` combinations (i.e., two `zone_air_temperature_sensor` fields for VAV-123)
- An invalid `standardFieldName` (i.e., not defined in the referenced ontology, mispelled, etc.)
- Missing BACnet info in the columns (e.g., blank `objectId`)

#### Step 9 - Type match to the ontology
When no validation errors are present, assets in the loadsheet can be matched to DBO entity types. Matching attempts to find the closest canonical type in the DBO that has the same fieldset as the asset in the loadsheet.
```
match
```

#### Step 10 - Perform a review of type matches and assign to a valid canonical type.
You can review all DBO general types found in the loadsheet (i.e., AHU, VAV, FCU, etc.)
```
review generalTypes
```

Or, you can review specific DBO general types found in the loadsheet
```
review generalTypes VAV
```

Or, you can review sub-sets (distinct field sets) of general types found in the loadsheet
```
review generalTypes VAV 1
```

Or, you can review matched types (i.e., the field set in the loadsheet matched to a DBO type
TODO: verify this is the behavior of this command
```
review matches
```


#### Step 11 - Apply the matched types
TODO: explain match types in detail
1. You can review all matches (close, incomplete, and exact) using `apply all`
```
apply all
```

2. OR you can auto-apply "exact" matches and only review inexact (close and imcomplete) using `apply close`
```
apply close
```

#### Step 12 - Export the loadsheet with applied matches for final type review
```
export excel '../loadsheet/Loadsheet_ALC_Normalized.xlsx'
```

#### Step 13 - Convert normalized loadsheet to ABEL spreadsheet:
Import discovery file (payload) and a building config (bc) for the tool to populate:
- entity information: code, guid, etag
- payload information: raw units and states
```
import payload 'path/to/payload.csv'
import bc 'path/to/bc.yaml'
convert abel
```
The ABEL formatted spreadsheet will be exported to the same directory as the loadsheet with suffix "_abel".

## Known Deficiencies and Future Development

The following is a list of issues that need to be addressed before widespread use:
* Add rigorous typing to all methods
* Make the necessary fields in `handler.py` and `representations.py` private
* Increase the match success rate of the rules JSON (and potentially provide tooling or templates for users to create their own ruleset)
* Expand to type match to more domains (currently only HVAC)

## Optional Unit Tests
### Ontology validation tests
Manual (optional) unit tests:
- Add a fake field with invalid subfields `bacon_sensor` to the ontology field list (../resources/fields/telemetry_fields.yaml) -- should return error
- Add a fake field with valid subfields `supply_sensor` to the ontology field list (../resources/fields/telemetry_fields.yaml) -- will NOT return an error.
- Add a new abstract type with a fake field -- should return error
- Add duplicate fields to fake abstract type -- should return error
