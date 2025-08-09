import re
from typing import List, Optional

class LoadsheetValidationChecks:
    def __init__(self):
        pass

    def validate_required_columns(df):
        """
        Ensures that all the required columns are present in the loadsheet.
        """

        required_columns = [
            "location", "controlProgram", "name", "type", "path", "deviceId", 
            "objectType", "objectId", "objectName", "units", "required", 
            "isMissing", "manuallyMapped", "building", "generalType", 
            "typeName", "assetName", "fullAssetPath", "standardFieldName"
        ]
        missing_columns = [col for col in required_columns if col not in df.columns]

        if missing_columns:
            print("❌ The following required columns are missing from the loadsheet:")
            for col in missing_columns:
                print(f" - {col}")
            return False
        else:
            return True

    def validate_no_leading_trailing_spaces(df):
        """
        Checks for and flags any leading or trailing spaces in listed columns.
        """

        columns_to_check = [
            "location", "controlProgram", "name", "type", "path", "deviceId",
            "objectType", "objectId", "objectName", "units", "required",
            "isMissing", "manuallyMapped", "building", "generalType",
            "typeName", "assetName", "fullAssetPath", "standardFieldName"
        ]
        failed_rows = []

        for col in columns_to_check:
            if col not in df.columns:
                # Skip missing columns — or optionally report them elsewhere
                continue

            # Only check rows where the value is a string
            for idx, val in df[col].items():
                if isinstance(val, str):
                    if val != val.strip():
                        excel_row = idx + 2  # Excel row numbering
                        failed_rows.append((excel_row, col, val))

        if failed_rows:
            print("❌ Leading or trailing spaces found in columns:")
            for row_num, col, val in failed_rows:
                print(f"Row {row_num}, column '{col}': '{val}'")
            return False
        else:
            return True

    def validate_required_column(df):
        """
        Validates that every row of the 'required' column only contains 'YES' or 'NO' (case-insensitive).
        """

        if 'required' not in df.columns:
            print("❌ Error: 'required' column not found.")
            return None

        df['required_cleaned'] = df['required'].astype(str).str.strip().str.upper()
        invalid_required = df[~df['required_cleaned'].isin(['YES', 'NO'])]

        if not invalid_required.empty:
            print("❌ Invalid entries in 'required' column:")
            for idx, _ in invalid_required.iterrows():
                print(f"Row {idx + 2}")
            return None  # Fail
        
        return df  # Pass

    def validate_required_fields_populated(df):
        """
        Ensures the following fields are populated for every row where 'required' = 'YES' and 'isMissing' = 'NO.
        """

        columns_to_check = [ 
            "location", "controlProgram", "name", "type", "path",
            "deviceId", "objectType", "objectId"
        ]

        failed_rows = []

        # Normalize case and strip for filtering columns
        required_mask = df['required'].astype(str).str.strip().str.upper() == 'YES'
        not_missing_mask = df['isMissing'].astype(str).str.strip().str.upper() == 'NO'

        filtered_df = df[required_mask & not_missing_mask]

        for idx, row in filtered_df.iterrows():
            missing_cols = []
            for col in columns_to_check:
                val = str(row.get(col, '')).strip()
                if val == '' or val.lower() == 'nan':
                    missing_cols.append(col)

            if missing_cols:
                excel_row = idx + 2  # Excel row numbering
                failed_rows.append((excel_row, missing_cols))

        if failed_rows:
            print("❌ Rows with required='YES' and isMissing='NO' must have these fields populated:")
            for row_num, cols in failed_rows:
                print(f"Row {row_num}: Missing or blank columns: {cols}")
            return False
        else:
            return True

    def validate_missing_required_rows(df):
        """
        Ensures that the following fields are blank or non-blank for every row where 'required' = 'YES' and 'isMissing' = 'YES'.
        """

        must_be_blank = [
            "name", "type", "path",
            "deviceId", "objectType", "objectId", "objectName"
        ]

        must_not_be_blank = [
            "building", "generalType",
            "assetName", "fullAssetPath", "standardFieldName"
        ]

        failed_rows = []

        # Filter relevant rows
        required_yes = df['required'].astype(str).str.strip().str.upper() == 'YES'
        is_missing_yes = df['isMissing'].astype(str).str.strip().str.upper() == 'YES'
        filtered_df = df[required_yes & is_missing_yes]

        for idx, row in filtered_df.iterrows():
            excel_row = idx + 2
            issues = []

            # Check must-be-blank fields
            for col in must_be_blank:
                val = str(row.get(col, '')).strip()
                if val and val.lower() != 'nan':
                    issues.append(f"{col} should be blank (found '{val}')")

            # Check must-not-be-blank fields
            for col in must_not_be_blank:
                val = str(row.get(col, '')).strip()
                if not val or val.lower() == 'nan':
                    issues.append(f"{col} must not be blank")

            if issues:
                failed_rows.append((excel_row, issues))

        if failed_rows:
            print("❌ Validation failed for rows where required='YES' and isMissing='YES':")
            for row_num, issues in failed_rows:
                print(f"Row {row_num}:")
                for issue in issues:
                    print(f"  - {issue}")
            return False
        else:
            return True

    def validate_all_standard_field_names(df, ontology):
        """
        Ensures all standardFieldNames are valid telemetry fields within the DBO. 
        """
        required_yes = df[df['required_cleaned'] == 'YES']
        invalid_rows = []

        for idx, row in required_yes.iterrows():
            field_name = str(row.get('standardFieldName', '')).strip()
            excel_row = idx + 2  # Adjust for header + zero indexing

            if field_name == "":
                invalid_rows.append((excel_row, field_name))

            if not field_name:
                invalid_rows.append((excel_row, "<BLANK>"))
                continue

            global_namespace_string = 'GLOBAL'
            namespace_list = ['', 'HVAC', 'LIGHTING']
            valid_namespaces = []
            for namespace in namespace_list:
                standard_field = StandardField(namespace, field_name)
                print(dir(ontology))
                if ontology.IsFieldValid(standard_field):
                    if not namespace:
                        valid_namespaces.append(global_namespace_string)
                    else:
                        valid_namespaces.append(namespace)

            if not valid_namespaces:
                invalid_rows.append((excel_row, field_name))

        if invalid_rows:
            print("❌ Invalid or missing 'standardFieldName' entries:")
            for excel_row, field in invalid_rows:
                print(f"Row {excel_row}: '{field}'")
            return False
        else:
            return True

    def validate_units(df, ontology):
        """
        Ensures that all units match the expected DBO units based on standardFieldName.

        Example: 
            - standardFieldName = 'discharge_air_temperature_setpoint'
            - Expected DBO units = kelvin, degrees-celsius, or degrees-fahrenheit
            - Actual units = degrees-fahrenheit
            - Check is successful ✅
        """
        required_yes = df[df['required_cleaned'] == 'YES']
        invalid_unit_rows = []
        no_unit_keywords = ['alarm', 'count', 'mode']

        for idx, row in required_yes.iterrows():
            field = str(row.get('standardFieldName', '')).strip()
            excel_row = idx + 2
            # Normalize units by replacing dashes with underscores
            unit_in_sheet = str(row.get('units', '')).strip().lower().replace('-', '_')

            if any(keyword in field for keyword in no_unit_keywords):
                continue

            words = field.split('_')
            found_units = False
            valid_units_set = set()

            for word in words:
                try:
                    unit_keys = ontology.universe.unit_universe.GetUnitsForMeasurement(word).keys()
                    if unit_keys:
                        found_units = True
                        valid_units_set.update([u.lower() for u in unit_keys])
                except Exception:
                    continue

            if not found_units:
                units = row.get('units', '')
                if units == 'no-units':
                    continue  # treat as val
                invalid_unit_rows.append((excel_row, field, row.get('units', '')))
                continue

            if unit_in_sheet not in valid_units_set:
                invalid_unit_rows.append((excel_row, field, row.get('units', '')))

        if invalid_unit_rows:
            print("\n❌ Rows with units that do not match ontology units:")
            for excel_row, field, unit_val in invalid_unit_rows:
                print(f"Row {excel_row}: standardFieldName='{field}', units='{unit_val}'")

        if invalid_unit_rows:
            return False
        else:
            return True

    def validate_full_asset_path(df):
        """
        Checks that 'fullAssetPath' follows the format 'building:generalType:assetName' for all rows where 'required' = 'YES'.
        """

        if 'fullAssetPath' not in df.columns:
            print("❌ Error: 'fullAssetPath' column not found.")
            return False

        required_yes = df[df['required_cleaned'] == 'YES']
        invalid_rows = []

        for idx, row in required_yes.iterrows():
            building = str(row.get('building', '')).strip()
            general_type = str(row.get('generalType', '')).strip()
            asset_name = str(row.get('assetName', '')).strip()
            expected_path = f"{building}:{general_type}:{asset_name}"

            actual_path = str(row.get('fullAssetPath', '')).strip()
            excel_row = idx + 2

            # Check if actual_path matches expected_path exactly
            if actual_path != expected_path:
                invalid_rows.append((excel_row, actual_path or "<BLANK>", expected_path))

        if invalid_rows:
            print("❌ Invalid 'fullAssetPath' entries (expected 'building:generalType:assetName'):")
            for excel_row, actual, expected in invalid_rows:
                print(f"Row {excel_row}: actual='{actual}', expected='{expected}'")
            return False
        else:
            return True

    def validate_object_type_for_command_status(df):
        """
        Validates that standardFieldNames containing 'run_command', 'run_status', 'damper_command', 'damper_status',
        'valve_command', or 'valve_status' have an objectType of 'BV', 'BI', 'BO', or 'MSV'. Only enforced when required='YES' and isMissing='NO'.
        """

        target_keywords = {
            'run_command', 'run_status',
            'damper_command', 'damper_status',
            'valve_command', 'valve_status'
        }
        valid_object_types = {'BV', 'BI', 'BO', 'MSV'}
        failed_rows = []

        # Filter to required == YES and isMissing == NO
        required_yes = df['required'].astype(str).str.strip().str.upper() == 'YES'
        is_missing_no = df['isMissing'].astype(str).str.strip().str.upper() == 'NO'
        filtered_df = df[required_yes & is_missing_no]

        for idx, row in filtered_df.iterrows():
            standard_field = str(row.get('standardFieldName', '')).strip().lower()
            object_type = str(row.get('objectType', '')).strip().upper()
            excel_row = idx + 2

            if any(keyword in standard_field for keyword in target_keywords):
                if object_type not in valid_object_types:
                    failed_rows.append((excel_row, standard_field, object_type or "<BLANK>"))

        if failed_rows:
            print("❌ Invalid objectType for control/status-related standardFieldNames (required='YES' and isMissing='NO'):")
            for row_num, field, obj_type in failed_rows:
                print(f"Row {row_num}: standardFieldName='{field}', objectType='{obj_type}' (must be one of {sorted(valid_object_types)})")
            return False
        else:
            return True

    def validate_object_type_for_measurement_points(df):
        """
        Validates that standardFieldNames ending in '_sensor', '_setpoint', '_count', or '_percentage'
        have an objectType of 'AV', 'AI', or 'AO'. Only enforced when required='YES' and isMissing='NO'.
        """

        target_suffixes = ['_sensor', '_setpoint', '_count', '_percentage']
        valid_object_types = {'AV', 'AI', 'AO'}
        failed_rows = []

        # Filter to required == YES and isMissing == NO
        required_yes = df['required'].astype(str).str.strip().str.upper() == 'YES'
        is_missing_no = df['isMissing'].astype(str).str.strip().str.upper() == 'NO'
        filtered_df = df[required_yes & is_missing_no]

        for idx, row in filtered_df.iterrows():
            standard_field = str(row.get('standardFieldName', '')).strip().lower()
            object_type = str(row.get('objectType', '')).strip().upper()
            excel_row = idx + 2

            if any(suffix in standard_field for suffix in target_suffixes):
                if object_type not in valid_object_types:
                    failed_rows.append((excel_row, standard_field, object_type or "<BLANK>"))

        if failed_rows:
            print("❌ Invalid objectType for sensor/setpoint/count/percentage standardFieldNames (required='YES' and isMissing='NO'):")
            for row_num, field, obj_type in failed_rows:
                print(f"Row {row_num}: standardFieldName='{field}', objectType='{obj_type}' (must be one of {sorted(valid_object_types)})")
            return False
        else:
            return True

    def validate_alarm_types(df):
        """
        Ensures that standardFieldNames containing 'alarm' have a type value of 'BALM'.
        """
        
        required_yes = df[df['required_cleaned'] == 'YES']
        invalid_rows = []

        for idx, row in required_yes.iterrows():
            field_name = str(row.get('standardFieldName', '')).lower()
            field_type = str(row.get('type', '')).strip()
            excel_row = idx + 2

            if 'alarm' in field_name and field_type != 'BALM':
                invalid_rows.append((excel_row, field_name, field_type))

        if invalid_rows:
            print("❌ Rows where standardFieldName contains 'alarm' but type is not 'BALM':")
            for row_num, sf_name, t_val in invalid_rows:
                print(f"Row {row_num}: standardFieldName='{sf_name}', type='{t_val}'")
            return False
        return True

    def validate_unique_standard_fields_per_asset(df):
        """
        Confirms that each standardFieldName is unique within a given assetName.
        """
        
        required_yes = df[df['required_cleaned'] == 'YES']
        duplicates = []

        # Group by assetName and look for duplicated standardFieldNames
        grouped = required_yes.groupby('assetName')

        for asset, group in grouped:
            # Get standardFieldNames and count duplicates
            duplicates_in_group = group[group.duplicated('standardFieldName', keep=False)]
            if not duplicates_in_group.empty:
                for idx, row in duplicates_in_group.iterrows():
                    excel_row = idx + 2
                    duplicates.append((excel_row, asset, row['standardFieldName']))

        if duplicates:
            print("❌ Duplicate standardFieldNames found for the same assetName:")
            for row_num, asset, field in duplicates:
                print(f"Row {row_num}: assetName='{asset}', standardFieldName='{field}'")
            return False
        return True

    def validate_typename_matches_standard_fields(df, ontology):
        """
        Verifies that the set of standardFieldNames assigned to each assetName exactly matches 
        the expected set defined in the ontology for the given typeName.
        """
        
        required_yes = df[df['required_cleaned'] == 'YES']
        grouped = required_yes.groupby('assetName')

        failed_assets = []

        for asset_name, group in grouped:
            standard_fields = group['standardFieldName'].astype(str).str.strip().tolist()
            type_name = group['typeName'].iloc[0]

            if not CompareFieldsToSpecifiedType(ontology, True, type_name, standard_fields):
                for idx in group.index:
                    excel_row = idx + 2
                    failed_assets.append((excel_row, asset_name, type_name))

        if failed_assets:
            print("❌ standardFieldNames do not 100% match typeName definitions:")
            seen = set()
            for row_num, asset, type_name in failed_assets:
                seen_length = len(seen)
                seen.add(asset)
                if len(seen) > seen_length:
                    print(f"assetName='{asset}', typeName='{type_name}'")
            return False
        else:
            return True

    def validate_unique_typename_per_asset(df):
        """
        Ensures that each assetName maps to a single unique typeName. In other words, 
        there are not multiple typeNames within a single assetName. Blank typeNames are ignored.
        """
        grouped = df.groupby('assetName')

        failed_assets = []

        for asset_name, group in grouped:
            type_names = (
                group['typeName']
                .dropna()
                .astype(str)
                .str.strip()
            )
            type_names = type_names[type_names != 'nan'].unique()

            if len(type_names) > 1:
                for idx in group.index:
                    excel_row = idx + 2  # Excel rows are 1-indexed, + header row
                    failed_assets.append((excel_row, asset_name, type_names.tolist()))

        if failed_assets:
            print("❌ Each assetName must have only one unique typeName (excluding blanks):")
            seen = set()
            for row_num, asset, type_names in failed_assets:
                if asset not in seen:
                    print(f"assetName='{asset}' has multiple typeNames: {type_names}")
                    seen.add(asset)
            return False
        else:
            return True


    def validate_required_flag_on_populated_rows(df):
        """
        Ensures that if any of the core identifying fields ('generalType', 'typeName', 'assetName',
        'fullAssetPath', or 'standardFieldName') are populated, then the 'required' column must be set to 'YES'.
        """
        
        check_fields = ['generalType', 'typeName', 'fullAssetPath', 'standardFieldName']
        failed_rows = []

        for idx, row in df.iterrows():
            required = str(row.get('required_cleaned', '')).strip().upper()

            # Identify all fields that are non-empty and not 'nan'
            non_blank_fields = {
                field: str(row.get(field, '')).strip()
                for field in check_fields
                if str(row.get(field, '')).strip() and str(row.get(field, '')).strip().lower() != 'nan'
            }

            if non_blank_fields and required != 'YES':
                # Use the first non-blank field for the error message
                failing_field, value = next(iter(non_blank_fields.items()))
                excel_row = idx + 2  # Excel-style row number
                failed_rows.append((excel_row, failing_field, value, required))

        if failed_rows:
            print("❌ Rows with populated fields must have required='YES':")
            for row_num, field, value, required in failed_rows:
                print(f"Row {row_num}: {field}='{value}', required='{required}'")
            return False
        else:
            return True

FQ_FIELD_NAME = re.compile(
    r'(^[a-z]+[a-z0-9]*(?:_[a-z]+[a-z0-9]*)*)((?:_[0-9]+)+)?$'
)

class StandardField(object):
  """A class to represent a generic field without increment or optionality.

  Args:
      namespace_name: a field's defined namespace as a string.
      standard_field_name: the un-incremented name of the field as a string.
        must be lower-case and properly formatted.
      increment: [Optional] a field's enumerated value suffixed onto the field
        name.

  Attributes:
      namespace: the name of the namespace as a string
      name: the field name as a string.
      increment: a field's enumerated value suffixed onto the field name.

  returns: An instance of the StandardField class.
  """

  def __init__(
      self,
      namespace_name: str,
      standard_field_name: str,
      increment: Optional[str] = '',
  ):
    super().__init__()
    if not FQ_FIELD_NAME.match(standard_field_name + increment):
      raise ValueError(
          f'{namespace_name}/{standard_field_name}{increment} format error'
      )

    else:
      self._namespace = namespace_name
    self._name = standard_field_name
    self._increment = increment

  def __hash__(self):
    return hash((self._namespace, self._name, self._increment))

  def __eq__(self, other):
    try:
      namespace_eq = self._namespace == other.GetNamespaceName()
      name_eq = self._name == other.GetStandardFieldName()
      increment_eq = self._increment == other.GetIncrement()
      return name_eq and namespace_eq and increment_eq
    except AttributeError as ae:
      print(ae)

  def __repr__(self):
    return f'{self._name}{self._increment}'

  def GetNamespaceName(self) -> str:
    """Returns namespace variable as a string."""
    return self._namespace

  def GetStandardFieldName(self) -> str:
    """Returns the unqualified field name.

    without any increment as a string
    """
    return self._name

  def GetIncrement(self) -> str:
    """Returns the EntityType Field's increment as a string."""
    return self._increment