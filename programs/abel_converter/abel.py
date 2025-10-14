# Copyright 2023 DB Engineering

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#    http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import numpy as np
import pandas as pd
from ruamel.yaml import YAML
import json
import uuid

from abel_converter import value_mapping

def safe_json_load(x):
    try:
        if pd.isna(x) or not str(x).strip():
            return None
        return json.loads(x)
    except (json.JSONDecodeError, TypeError):
        return {}
class Abel():
    def __init__(self):
        self.abel = {
            'Site': {
                'Building Code': None,
                'Entity Guid': None,
                'Etag': None
            },
            'Entities': {
                'Entity Code': None,
                'Display Name': None,
                'Entity Guid': None,
                'Is Existing': None,
                'Etag': None,
                'Is Reporting': None,
                'Cloud Device ID': None,
                'DBO Namespace': None,
                'DBO Entity Type Name': None,
                'Operation': None
            },
            'Entity Fields': {
                'DBO Standard Field Name': None,
                'Raw Field Name': None,
                'Reporting Entity Field': None,
                'Entity Code': None,
                'Entity Guid': None,
                'Reporting Entity Code': None,
                'Reporting Entity Guid': None,
                'Missing': None,
                'Raw Unit Path': None,
                'DBO Standard Unit Value': None,
                'Raw Unit Value': None
            },
            'States': {
                'Reporting Entity Code': None,
                'Reporting Entity Guid': None,
                'Reporting Entity Field': None,
                'DBO Standard State': None,
                'Raw State': None
            },
            'Connections': {
                'Source Entity Code': [],
                'Source Entity Guid': [],
                'DBO Connection Type': [],
                'Target Entity Code': [],
                'Target Entity Guid': []
            },
            'Loadsheet': None,
            'PhRED': None,
            'Log': {
                'Index': None,
                'Issue': None
            },
            'BMS Incorrect Units': None,
            'Existing Virtual Entities': None
        }

        self.site_code = None
        self.site_guid = None
        self.site_etag = None
        self.path = None

        self.entity_data = None
        self.entity_fields_data = None
        self.phred = None
        self.log = [] # logging issues/errors

        # Flags TBD
        self.LOADSHEET_IMPORTED = False
        self.PAYLOAD_IMPORTED = False

    def import_loadsheet(self, path):
        """
        Import legacy loadsheet.
        Args: 
            path: path to legacy ladsheet file.

        """
        self.path = path.split('.')[0]
        OBJECT_ID_MAPPING = {
            'AI': 'analog-input',
            'AV': 'analog-value',
            'AO': 'analog-output',
            'BV': 'binary-value',
            'BO': 'binary-output',
            'BI': 'binary-input',
            'MSV': 'multi-state-value'
        }
        loadsheet = pd.read_excel(path).sort_values(['assetName', 'standardFieldName'])
        loadsheet = loadsheet.loc[loadsheet['required']=='YES', :]
        loadsheet['fullAssetPath'] = loadsheet['building'] + ":" + loadsheet['generalType'] + ":" + loadsheet['assetName']
        loadsheet['deviceId'] = loadsheet.groupby('fullAssetPath')['deviceId'].ffill()
        loadsheet['deviceId'] = loadsheet.groupby('fullAssetPath')['deviceId'].bfill()
        self.abel['Loadsheet'] = loadsheet.to_dict()

        entity_fields = loadsheet.reset_index(drop=True)
        
        # Fill in blank deviceId and objectId for isMissing=YES
        entity_fields.loc[(entity_fields['isMissing']=="YES") & (entity_fields['objectType'].isna()==True), 'objectType'] = 'FV'
        mask = entity_fields['isMissing']=="YES"
        entity_fields.loc[mask, 'objectId'] = np.random.randint(10000, 11000, size=mask.sum())

        entity_fields['rawUnitValue'] = entity_fields['units'].str.replace('_', '-')
        entity_fields['units'] = entity_fields['standardFieldName'].apply(value_mapping.map_units).str.replace('-', '_')
        entity_fields['objectId'] = entity_fields['objectId'].astype(int)
        entity_fields['extendedObjectType'] = entity_fields['objectType'].map(OBJECT_ID_MAPPING)
        entity_fields['rawFieldName'] = 'data.' + entity_fields['extendedObjectType'] + '_' + entity_fields['objectId'].astype('str') + '.present-value'
        entity_fields['rawUnitPath'] = 'data.' + entity_fields['extendedObjectType'] + '_' + entity_fields['objectId'].astype('str') + '.units'
        entity_fields['Missing'] = entity_fields.apply(lambda x: 'TRUE' if x['isMissing'] == "YES" else "FALSE", axis=1)

        entity_fields.loc[entity_fields['Missing']=='TRUE', ['rawFieldName', 'rawUnitPath', 'units']] = np.nan # leave fields blank for missing points

        self.entity_fields_data = entity_fields[['path', 'deviceId', 'controlProgram', 'objectType', 'objectId', 'objectName', 'units', 
                                               'typeName', 'assetName', 'fullAssetPath', 'standardFieldName', 'Missing',
                                               'extendedObjectType', 'rawFieldName', 'rawUnitPath']]

        # Entity level data
        #
        # Virtual Entities
        deviceid_fullap = loadsheet[['deviceId', 'assetName', 'fullAssetPath']].drop_duplicates()
        count_id_by_fullap = deviceid_fullap.groupby(['fullAssetPath', 'assetName'], as_index=False).count()
        count_fullap_by_id = deviceid_fullap.groupby(['deviceId'], as_index=False).count()
        virtual_fullap = count_id_by_fullap.loc[count_id_by_fullap['deviceId'] > 1, 'fullAssetPath'].to_list()
        virtual_deviceid = count_fullap_by_id.loc[count_fullap_by_id['fullAssetPath'] > 1, 'deviceId'].to_list()

        virtual_entities = loadsheet[(loadsheet['deviceId'].isin(virtual_deviceid)==True)
                                        | (loadsheet['fullAssetPath'].isin(virtual_fullap)==True)]\
                                        [['fullAssetPath', 'typeName']]\
                                        .drop_duplicates()\
                                        .rename(columns={'fullAssetPath': 'entityCode',
                                                         'typeName': 'dboEntityTypeName'})\
                                        .sort_values('entityCode')

        virtual_entities['isReporting'] = 'FALSE'
        virtual_entities['dboNamespace'] = 'HVAC'
        virtual_entities['etag'] = np.nan
        virtual_entities['cloudDeviceId'] = np.nan
        # generate a new GUID for each unique virtual Entity
        virtual_entities['entityGuid'] = virtual_entities['entityCode'].apply(lambda x: uuid.uuid4()).astype('str')
        virtual_entities['deviceId'] = 'X' # to avoid merge on nulls in import_payload
        virtual_entities['dboGeneralType'] = virtual_entities['dboEntityTypeName'].apply(lambda x: x.split('_')[0])

        # Reporting Entities
        # Entities that are associated with multiple fullassetpaths are Passthrough
        reporting_passthrough = loadsheet[(loadsheet['deviceId'].isin(virtual_deviceid)==True)
                                                  | (loadsheet['fullAssetPath'].isin(virtual_fullap)==True)][['deviceId']]\
                                                  .drop_duplicates()
        reporting_passthrough['etag'] = np.nan
        reporting_passthrough['isReporting'] = 'TRUE'
        reporting_passthrough['dboNamespace'] = 'GATEWAYS'
        reporting_passthrough['dboGeneralType'] = 'PASSTHROUGH'
        reporting_passthrough['dboEntityTypeName'] = 'PASSTHROUGH'

        # Entities that are associated with one and only one fullassetpath are Passthrough
        reporting_not_passthrough = loadsheet[(loadsheet['deviceId'].isin(virtual_deviceid)==False)
                                                  & (loadsheet['fullAssetPath'].isin(virtual_fullap)==False)][['deviceId', 'assetName', 'typeName']]\
                                                  .drop_duplicates()\
                                                  .rename(columns={'typeName': 'dboEntityTypeName',
                                                                   'assetName': 'displayName'})
        reporting_not_passthrough['isReporting'] = 'TRUE'
        reporting_not_passthrough['dboNamespace'] = 'HVAC'
        reporting_not_passthrough['etag'] = np.nan
        reporting_not_passthrough['cloudDeviceId'] = np.nan
        reporting_not_passthrough['dboGeneralType'] = reporting_not_passthrough['dboEntityTypeName'].apply(lambda x: x.split('_')[0])

        self.entity_data = pd.concat([reporting_passthrough, reporting_not_passthrough, virtual_entities], axis=0)
        # self.entity_data.loc[() & (), 'displayName']

        self.LOADSHEET_IMPORTED = True
        

    def import_payload(self, path):
        """
        Import sample payload to pull available raw data values from.
        Args:
            path: path to sample payload file in json format.
            include_missing_entities: True - include entities with missing payload in ABEL spresdsheet, 
                                      False - exclude
                                      Default - False.
        
        The payload file must be exported from PhRED nonconfidential entities table.
        Use the Plx script below to get a discovery csv for all entities in the desired building,
        down load full result in csv format and feed the file path in this method:
        https://plx.corp.google.com/scripts2/script_46._66ecd6_a19c_4ed8_8a24_5baea50ff96a

        """     
        # for cases when discovery has empty data property
        DATA_PLACEHOLDER = {
            'units':'MISSING DATA',
            'state-text': 'MISSING DATA'
        }

        def enumerate_fields(dataframe):
            enum = dataframe.sort_values(['reportingEntityGuid', 'standardFieldName', 'rawFieldName'])\
                                [['reportingEntityGuid', 'standardFieldName', 'rawFieldName']]\
                                .drop_duplicates().reset_index(drop=True)
            enum['rawFieldName'] = enum['rawFieldName'].fillna('PLACEHOLDER')
            enum['fieldRank'] = enum.groupby(['reportingEntityGuid', 'standardFieldName'], as_index=False)['standardFieldName']\
                                          .rank(method="first", ascending=True, na_option='keep')
            enum['fieldCount'] = enum.groupby(['reportingEntityGuid', 'standardFieldName'], as_index=False)['standardFieldName']\
                                          .rank(method="max", ascending=True, na_option='keep')
            enum['fieldEnum'] = enum.apply(lambda x: '' if x['fieldCount']==1 else ('_'+str(int(x['fieldRank']))), axis=1)
            enum['reportingEntityField'] = enum['standardFieldName'] + enum['fieldEnum']
            enum['rawFieldName'] = enum.apply(lambda x: np.nan if x['rawFieldName']=='PLACEHOLDER' else x['rawFieldName'], axis=1)

            dataframe = dataframe.merge(enum[['reportingEntityGuid', 'rawFieldName', 'standardFieldName', 'reportingEntityField']],
                           how='left',
                           on=['reportingEntityGuid', 'rawFieldName', 'standardFieldName'],
                           left_index=False,
                           right_index=False)

            dataframe['fieldRankMissing'] = dataframe.groupby(['reportingEntityGuid', 'standardFieldName'], as_index=False)['standardFieldName']\
                                          .rank(method="first", ascending=True, na_option='keep')
            dataframe['fieldCountMissing'] = dataframe.groupby(['reportingEntityGuid', 'standardFieldName'], as_index=False)['standardFieldName']\
                                          .rank(method="max", ascending=True, na_option='keep')
            dataframe['fieldEnumMissing'] = dataframe.apply(lambda x: '' if x['fieldCountMissing']==1 else ('_'+str(int(x['fieldRankMissing']))), axis=1)
            
            #enumerate missing fields separately
            dataframe['reportingEntityField'] = dataframe.apply(lambda x: (x['reportingEntityField']+x['fieldEnumMissing'])
                                                                            if x['rawFieldName'] is np.nan
                                                                            else x['reportingEntityField'], axis=1)
            dataframe.drop(['fieldRankMissing', 'fieldCountMissing', 'fieldEnumMissing'], axis=1, inplace=True)

            return dataframe

        def get_states(active, inactive, multi):
            if all([not active, not inactive, not multi]):
                return ['active', 'inactive']
            if active and inactive:
                return ['active', 'inactive']
            if isinstance(multi, list):
                return [(ix+1, val) for ix, val in enumerate(multi)] if multi else np.nan
            if isinstance(multi, str):
                return ['active', 'inactive']
        
        if not path:
            return
        
        payload_data = pd.read_csv(path, dtype={'externalId':'str'})
        payload_data.columns = ['externalId', 'deviceId', 'entity_code', 'entity_guid', 'building',
                                'building_guid', 'created', 'discoveryresult']
        payload_data.dropna(how='any', inplace=True)
        payload_data.loc[payload_data['entity_code'].isna()==False, 'code'] = 'EMPTY CODE: PLACEHOLDER'

        self.site_code = payload_data.loc[0, 'building']
        self.site_guid = payload_data.loc[0, 'building_guid']

        payload_data['discoveryresult'] = payload_data['discoveryresult'].apply(safe_json_load)

        payload_data['rawFieldName'] = payload_data['discoveryresult'].apply(lambda x: list(x['data'].keys()) if x.get('data') else ['MISSING DATA'])
        payload_data = payload_data.explode('rawFieldName')

        payload_data['data'] = payload_data.apply(lambda x: x['discoveryresult']['data'].get(x['rawFieldName']) if x['discoveryresult'].get('data') else DATA_PLACEHOLDER, axis=1)

        payload_data['rawUnitValue'] = payload_data.apply(lambda x: x['data'].get('units', 'MISSING'), axis=1) # upd 6/27 must be actual raw value from payload
        payload_data['state'] = payload_data.apply(lambda x: get_states(x['data'].get('active-text'), 
                                                    x['data'].get('inactive-text'),
                                                    x['data'].get('state-text', None)), axis=1)

        payload_data['rawFieldName'] =  payload_data['rawFieldName'].apply(lambda x: 'data.' + x + '.present-value')
        payload_data['deviceId'] = payload_data['deviceId'].str.replace('bacnet:', 'DEV:')
        payload_data = payload_data.rename(columns={'externalId': 'cloudDeviceId',
                                     'entity_code': 'entityCode',
                                     'entity_guid': 'reportingEntityGuid'
                                    })
        payload_data.drop(['data', 'discoveryresult'], axis=1, inplace=True)

        payload_df = payload_data[['deviceId', 'rawFieldName', 'state', 'rawUnitValue']]
        self.payload = payload_df.copy()

        self.phred = payload_data[['deviceId', 'entityCode', 'cloudDeviceId', 'reportingEntityGuid']]\
                                                                                    .drop_duplicates()\
                                                                                    .rename(columns={
                                                                                        'entityCode': 'phred_entityCode', 
                                                                                        'cloudDeviceId': 'phred_cloudDeviceId', 
                                                                                        'reportingEntityGuid': 'phred_reportingEntityGuid'
                                                                                        })
        self.abel['PhRED'] = self.phred.to_dict()

        ### CHECK DEVICES
        loadsheet_dev = self.entity_fields_data['deviceId'].unique().tolist()
        phred_dev = self.phred['deviceId'].unique().tolist()

        missing_dev = [dev for dev in loadsheet_dev if dev not in phred_dev]

        for dev in missing_dev:
            print((f'Required Device is missing in PhRED: {dev}'))
            self.log.append(f'Required device is missing in PhRED: {dev}')

        ### CHECK OBJECTS
        loadsheet_obj = self.entity_fields_data[self.entity_fields_data['Missing']=='FALSE'][['deviceId', 'rawFieldName']].drop_duplicates()
        loadsheet_obj['in_loadsheet'] = 'TRUE'
        phred_obj = payload_df[['deviceId', 'rawFieldName']].drop_duplicates()
        phred_obj['in_phred'] = 'TRUE'

        mismatch = loadsheet_obj.merge(phred_obj,
                            how='left',
                            on=['deviceId', 'rawFieldName'],
                            left_index=False,
                            right_index=False)

        mismatch = mismatch[mismatch['in_phred'].isna()==True].sort_values(['deviceId', 'rawFieldName'])

        for i in range(len(mismatch)):
            vals = mismatch.iloc[i]
            print(f'Required Object missing in PhRED: {vals.deviceId}, {vals.rawFieldName}')
            self.log.append(f'Required object missing in PhRED: {vals.deviceId}, {vals.rawFieldName}')

        #### UPDATE ENTITY DATA ###
        self.entity_data = self.entity_data.merge(self.phred,
                                                  how='left',
                                                  on=['deviceId'],
                                                  left_index=False,
                                                  right_index=False)
        self.entity_data['entityCode'] = self.entity_data.apply(lambda x: x['phred_entityCode'] if x['isReporting']=='TRUE' 
                                                                            else x['entityCode'], axis=1)
        self.entity_data['entityCode'] = self.entity_data.apply(lambda x: 'MISSING CODE: '+x['deviceId'] if all([pd.isnull(x['phred_entityCode']),
                                                                                                            x['isReporting']=='TRUE']) else x['entityCode'], axis=1)
        
        self.entity_data['cloudDeviceId'] = self.entity_data.apply(lambda x: x['phred_cloudDeviceId'] if x['isReporting']=='TRUE' else np.nan, axis=1)
        self.entity_data['cloudDeviceId'] = self.entity_data.apply(lambda x: 'MISSING ID: '+x['deviceId'] if all([pd.isnull(x['phred_cloudDeviceId']),
                                                                                                            x['isReporting']=='TRUE']) else x['cloudDeviceId'], axis=1)
        
        self.entity_data['entityGuid'] = self.entity_data.apply(lambda x: x['phred_reportingEntityGuid'] if x['isReporting']=='TRUE' else x['entityGuid'], axis=1)
        self.entity_data['entityGuid'] = self.entity_data.apply(lambda x: 'MISSING GUID: '+x['deviceId'] if all([pd.isnull(x['phred_reportingEntityGuid']),
                                                                                                            x['isReporting']=='TRUE']) else x['entityGuid'], axis=1)
        self.entity_data['Operation'] = np.nan
        self.entity_data.drop(['phred_cloudDeviceId', 'phred_entityCode', 'phred_reportingEntityGuid'], axis=1, inplace=True)
        self.entity_data = self.entity_data[['entityCode', 'displayName', 'deviceId', 'entityGuid', 'etag', 'isReporting', 'cloudDeviceId', 'dboNamespace', 'dboGeneralType', 'dboEntityTypeName', 'Operation']]


        #### UPDATE ENTITY FIELDS DATA ###
        self.entity_fields_data = self.entity_fields_data.merge(self.payload,
                                                                how='left', 
                                                                on=['deviceId', 'rawFieldName'], 
                                                                left_index=False, 
                                                                right_index=False)

        # Add Entity Guid to Entity Fields
        entity_guids = self.entity_data[['entityCode', 'entityGuid']].drop_duplicates().rename(columns={'entityCode':'fullAssetPath'})
        self.entity_fields_data = self.entity_fields_data.merge(entity_guids, 
                                                                how='left', 
                                                                on='fullAssetPath', 
                                                                left_index=False, 
                                                                right_index=False)

        # Add Reporting Entity Code and Reporting Entity Guid
        reporting_entity_data = self.entity_data[['deviceId', 'entityCode', 'entityGuid']]\
                                                        .drop_duplicates()\
                                                        .rename(columns={'entityCode': 'reportingEntityCode', 
                                                                         'entityGuid' :'reportingEntityGuid'})
        # Add Entity Code and Entity Guid 
        self.entity_fields_data = self.entity_fields_data.merge(reporting_entity_data,
                                                                how='left',
                                                                on=['deviceId'], 
                                                                left_index=False, 
                                                                right_index=False)

        # fill in missing Entity Guids with placeholder to prevent error in enumeration
        self.entity_fields_data['reportingEntityGuid'] = self.entity_fields_data.apply(lambda x: 'MISSING IN PHRED:'+x['deviceId'] if x['reportingEntityGuid'] is np.nan else x['reportingEntityGuid'], axis=1)
        
        # Replace Entity Code with Reporting Entity Code in Entity Fields for non-modelled Entities:
        self.entity_fields_data['entityCode'] = self.entity_fields_data.apply(lambda x: x['reportingEntityCode'] if x['entityGuid'] is np.nan else x['fullAssetPath'], axis=1)

        # Enumerate fields by Reporting Entity Guid
        self.entity_fields_data = enumerate_fields(self.entity_fields_data)

        # Raw Unit Path, DBO Standard Unit Value, Raw Unit Value must be blank for binary and multi-state fields
        self.entity_fields_data.loc[(self.entity_fields_data['rawFieldName'].str.contains('binary')==True) 
                                    | (self.entity_fields_data['rawFieldName'].str.contains('multi-state')==True), ['rawUnitPath', 'rawUnitValue', 'units']] = ''
        
        # Check if raw BMS units match the standard units and flag the mismatching ones for manual review
        self.entity_fields_data['unitsCheck'] = np.nan
        self.entity_fields_data['unitsCheck'] = self.entity_fields_data['unitsCheck'].astype(object)
        
        self.entity_fields_data.loc[(self.entity_fields_data['units'].str.replace("_", "-") != self.entity_fields_data['rawUnitValue'].str.replace("_", "-")) & 
                                    (self.entity_fields_data['Missing']=='FALSE') &
                                    (self.entity_fields_data['rawUnitValue'].isna()==False), 
                                    'unitsCheck'] = 'Incorrect units in BMS'

        #### ADD AND MAP STATES DATA
        states = self.entity_fields_data.loc[(self.entity_fields_data['Missing']=='FALSE')]   # filter out missing points
        states = states.loc[(states['rawFieldName'].str.contains('binary')==True) 
                                    | (self.entity_fields_data['rawFieldName'].str.contains('multi-state')==True)]\
                                   [['reportingEntityCode', 'reportingEntityField', 'standardFieldName', 'state', 'reportingEntityGuid']]          # get binary and multistate fields
        # add state placeholders
        state_placeholder = 'active, inactive'
        states.loc[states['state'].isna()==True, 'state'] = states.loc[states['state'].isna()==True, 'state'].apply(lambda x: state_placeholder.split(', ') if pd.isna(x) else x)

        states = states.explode('state').sort_values(['reportingEntityCode', 'reportingEntityField']).drop_duplicates()                   # flatten states
        states['rawStateValue'] = states.state.apply(lambda x: x[1] if isinstance(x, tuple) else "")
        states['rawState'] = states.state.apply(lambda x: x[0] if isinstance(x, tuple) else x)
        states['dboStandardState'] = states.apply(lambda x: value_mapping.map_states(x['standardFieldName'], x['state']), axis=1)   # map raw states to dbo standard states

        self.states_data = states[['reportingEntityCode', 'reportingEntityGuid', 'reportingEntityField', 'dboStandardState', 'rawState', 'rawStateValue']]

        # Clear Reporting Entity Field for Reporting Entities that are not linked to any Virtual Entities (otherwise validation fails)
        self.entity_fields_data.loc[self.entity_fields_data['entityGuid'].isna()==True, 'reportingEntityField'] = np.nan

        incorrect_units = self.entity_fields_data.loc[self.entity_fields_data['unitsCheck'].isna()==False, 
                                                      ['controlProgram', 'deviceId', 'objectType', 'objectId', 'objectName', 'standardFieldName', 'rawUnitValue', 'units']].drop_duplicates()
        incorrect_units['objectId'] = incorrect_units['objectType'] + ":" + incorrect_units['objectId'].astype(str)
        incorrect_units.drop('objectType', axis=1, inplace=True)
        incorrect_units.columns = ['ControlProgram', 'deviceId', 'objectId', 'objectName', 'Normalized Field Name', 'Current BMS Units', 'Correct Units']
        self.abel['BMS Incorrect Units'] = incorrect_units.to_dict()

        # Replace incorrect units with correct ones
        self.entity_fields_data['rawUnitValue'] = self.entity_fields_data.apply(lambda x: x['units'].replace("_", "-") if (type(x['units'])==str and x['units']!=x['rawUnitValue']) else x['rawUnitValue'], axis=1)

        self.PAYLOAD_IMPORTED = True

    def import_building_config(self, path):
        yaml = YAML(typ='rt')
        with open(path) as f:
            building_config = yaml.load(f)

        # update etags:
        self.site_etag = building_config.get(self.site_guid).get('etag') if building_config.get(self.site_guid) else np.nan
        if type(self.entity_data)==pd.DataFrame:
            self.entity_data['etag'] = self.entity_data['entityGuid'].apply(lambda x: building_config.get(x).get('etag') if building_config.get(x) else np.nan)

        existing_virtual_entities = {}

        # search for existing virtual entities and replace "new" virtual entities with existing ones
        for key, val in building_config.items():
            if val.get('links'):
                existing_virtual_entities[val.get('code')] = {'guid' : key,
                                                              'etag': str(val.get('etag'))}
        if type(self.entity_data)==pd.DataFrame:
            self.entity_data['isExisting'] = ''
            for key, val in existing_virtual_entities.items():
                self.entity_data.loc[self.entity_data['entityCode']==key, 'isExisting'] = ['YES']
                self.entity_data.loc[self.entity_data['entityCode']==key, 'entityGuid'] = val.get('guid')
                self.entity_data.loc[self.entity_data['entityCode']==key, 'etag'] = str(val.get('etag'))
                self.entity_data.loc[self.entity_data['entityCode']==key, 'entityCode'] = key
                self.entity_fields_data.loc[self.entity_fields_data['entityCode']==key, 'entityGuid'] = val.get('guid')
                self.entity_fields_data.loc[self.entity_fields_data['entityCode']==key, 'entityCode'] = key
        if len(existing_virtual_entities) > 0:
            ex_ve_df = pd.DataFrame.from_dict(existing_virtual_entities).transpose().reset_index().sort_values('index')
            ex_ve_df.columns = ['code', 'guid', 'etag']
            self.abel['Existing Virtual Entities'] = ex_ve_df.to_dict()
        
    def dump(self, path):
        """
        Export ABEL formatted building config in excel format.
        Args: 
            path: path to the export file.

        """
        with pd.ExcelWriter(path) as writer:
            for key in list(self.abel.keys()):
                pd.DataFrame(self.abel[key]).to_excel(writer, sheet_name=key, index=False, engine='xlsxwriter')


    def build(self):
        """
        Builds config from the legacy loadsheet.

        """
        # Site
        self.abel['Site']['Building Code'] = [self.site_code] if self.site_code else list(self.entity_fields_data.building.unique())
        self.abel['Site']['Entity Guid'] = [self.site_guid] if self.site_guid else [''] * len(self.entity_fields_data.building.unique())
        self.abel['Site']['Etag'] = [self.site_etag] if self.site_guid else [''] * len(self.entity_fields_data.building.unique())

        # Entity
        self.abel['Entities']['Entity Code'] = self.entity_data['entityCode']
        self.abel['Entities']['Display Name'] = self.entity_data['displayName']
        self.abel['Entities']['Entity Guid'] = self.entity_data['entityGuid']
        if 'isExisting' in self.entity_data:
            self.abel['Entities']['Is Existing'] = self.entity_data['isExisting'].to_list()
        self.abel['Entities']['Etag'] = self.entity_data['etag']
        self.abel['Entities']['Is Reporting'] = self.entity_data['isReporting']
        self.abel['Entities']['Cloud Device ID'] = self.entity_data['cloudDeviceId']
        self.abel['Entities']['DBO Namespace'] = self.entity_data['dboNamespace']
        self.abel['Entities']['DBO Entity Type Name'] = self.entity_data['dboEntityTypeName']
        self.abel['Entities']['Operation'] = self.entity_data['Operation']

        # Entity Fields
        self.abel['Entity Fields']['Entity Code'] = self.entity_fields_data['entityCode'].to_list()
        self.abel['Entity Fields']['Entity Guid'] = self.entity_fields_data['entityGuid'].to_list()
        self.abel['Entity Fields']['Reporting Entity Code'] = self.entity_fields_data['reportingEntityCode'].to_list()
        self.abel['Entity Fields']['Reporting Entity Guid'] = self.entity_fields_data['reportingEntityGuid'].to_list()
        self.abel['Entity Fields']['Reporting Entity Field'] = self.entity_fields_data['reportingEntityField'].tolist()
        self.abel['Entity Fields']['DBO Standard Field Name'] = self.entity_fields_data['standardFieldName'].to_list()
        self.abel['Entity Fields']['Missing'] = self.entity_fields_data['Missing'].to_list()
        self.abel['Entity Fields']['Raw Field Name'] = self.entity_fields_data['rawFieldName'].to_list()
        self.abel['Entity Fields']['Raw Unit Path'] = self.entity_fields_data['rawUnitPath'].to_list() 
        self.abel['Entity Fields']['Units Check'] = self.entity_fields_data['unitsCheck'].to_list() 
        self.abel['Entity Fields']['DBO Standard Unit Value'] = self.entity_fields_data['units'].to_list()
        self.abel['Entity Fields']['Raw Unit Value'] = self.entity_fields_data['rawUnitValue'].tolist()

        # States
        self.abel['States']['Reporting Entity Code'] = self.states_data['reportingEntityCode'].to_list()
        self.abel['States']['Reporting Entity Guid'] = self.states_data['reportingEntityGuid'].to_list()
        self.abel['States']['Reporting Entity Field'] = self.states_data['reportingEntityField'].to_list()
        self.abel['States']['DBO Standard State'] =  self.states_data['dboStandardState'].to_list()
        self.abel['States']['Raw State'] = self.states_data['rawState'].to_list()
        self.abel['States']['Raw State Value'] = self.states_data['rawStateValue'].to_list() # added this field in case manual mapping is necessary

        # Connections
        # TBD

        # Log
        self.abel['Log']['Index'] = [i+1 for i in range(len(self.log))]
        self.abel['Log']['Issue'] = self.log