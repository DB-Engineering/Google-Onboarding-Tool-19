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
import ruamel.yaml as yaml
import json
import uuid

from abel_converter import value_mapping


class Abel():
    def __init__(self):
        self.abel = {
            'Site': {
                'Building Code': None,
                'Entity Guid': None
            },
            'Entities': {
                'Entity Code': None,
                'Entity Guid': None,
                'Etag': None,
                'Is Reporting': None,
                'Cloud Device ID': None,
                'DBO Namespace': None,
                'DBO General Type': None,
                'DBO Entity Type Name': None
            },
            'Entity Fields': {
                'Entity Code': None,
                'Entity Guid': None,
                'Reporting Entity Code': None,
                'Reporting Entity Guid': None,
                'Reporting Entity Field': None,
                'DBO Standard Field Name': None,
                'Missing': None,
                'Raw Field Name': None,
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
            }
        }

        self.site_code = None
        self.site_guid = None
        self.path = None

        self.entity_data = None
        self.entity_fields_data = None
        self.phred = None
        self.log = []  # logging issues/errors

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
        entity_fields = pd.read_excel(path).sort_values(
            ['fullAssetPath', 'standardFieldName'])
        self.abel['Loadsheet'] = entity_fields.to_dict()

        entity_fields = entity_fields.loc[entity_fields['required'] == 'YES'].reset_index(
            drop=True)
        # excluding raw values from payload for now bc they are not trustworthy and prevent exporting of a correct building config
        entity_fields['rawUnitValue'] = entity_fields['units']
        entity_fields['units'] = entity_fields['units'].str.replace('-', '_')
        entity_fields['extendedObjectType'] = entity_fields['objectType'].map(
            OBJECT_ID_MAPPING)
        entity_fields['rawFieldName'] = 'data.' + entity_fields['extendedObjectType'] + \
            '_' + entity_fields['objectId'].astype('str') + '.present-value'
        entity_fields['rawUnitPath'] = 'data.' + entity_fields['extendedObjectType'] + \
            '_' + entity_fields['objectId'].astype('str') + '.units'
        entity_fields['Missing'] = entity_fields.apply(
            lambda x: 'TRUE' if x['controlProgram'] in value_mapping.MISSING_FILL else 'FALSE', axis=1)

        entity_fields.loc[entity_fields['Missing'] == 'TRUE', [
            'rawFieldName', 'rawUnitPath', 'units']] = np.nan  # leave fields blank for missing points

        self.entity_fields_data = entity_fields[['path', 'deviceId', 'objectType', 'objectId', 'objectName', 'units',
                                                 'required', 'building', 'generalType', 'typeName',
                                                 'assetName', 'fullAssetPath', 'standardFieldName', 'Missing',
                                                 'extendedObjectType', 'rawFieldName', 'rawUnitPath', 'rawUnitValue']]

        # Entity level data
        #
        # Virtual Entities
        deviceid_fullap = self.entity_fields_data[[
            'deviceId', 'fullAssetPath']].drop_duplicates()
        count_id_by_fullap = deviceid_fullap.groupby(
            ['fullAssetPath'], as_index=False).count()
        count_fullap_by_id = deviceid_fullap.groupby(
            ['deviceId'], as_index=False).count()
        virtual_fullap = count_id_by_fullap.loc[count_id_by_fullap['deviceId'] > 1, 'fullAssetPath'].to_list(
        )
        virtual_deviceid = count_fullap_by_id.loc[count_fullap_by_id['fullAssetPath'] > 1, 'deviceId'].to_list(
        )

        virtual_entities = self.entity_fields_data[(self.entity_fields_data['deviceId'].isin(virtual_deviceid) == True)
                                                   | (self.entity_fields_data['fullAssetPath'].isin(virtual_fullap) == True)][['fullAssetPath', 'generalType', 'typeName']]\
            .drop_duplicates()\
            .rename(columns={'fullAssetPath': 'entityCode',
                             'generalType': 'dboGeneralType',
                             'typeName': 'dboEntityTypeName'
                             })\
            .sort_values('entityCode')

        virtual_entities['isReporting'] = 'FALSE'
        virtual_entities['dboNamespace'] = 'HVAC'
        virtual_entities['etag'] = np.nan
        virtual_entities['cloudDeviceId'] = np.nan
        # # generate a new GUID for each unique virtual Entity
        virtual_entities['entityGuid'] = virtual_entities['entityCode'].apply(
            lambda x: uuid.uuid4()).astype('str')
        # to avoid merge on nulls in import_payload
        virtual_entities['deviceId'] = 'X'

        # Reporting Entities
        # Entities that are associated with multiple fullassetpaths are Passthrough
        reporting_passthrough = deviceid_fullap[(deviceid_fullap['deviceId'].isin(virtual_deviceid) == True)
                                                | (deviceid_fullap['fullAssetPath'].isin(virtual_fullap) == True)][['deviceId']].drop_duplicates()
        reporting_passthrough['etag'] = np.nan
        reporting_passthrough['isReporting'] = 'TRUE'
        reporting_passthrough['dboNamespace'] = 'GATEWAYS'
        reporting_passthrough['dboGeneralType'] = 'PASSTHROUGH'
        reporting_passthrough['dboEntityTypeName'] = 'PASSTHROUGH'

        # Entities that are associated with one and only one fullassetpath are Passthrough
        reporting_not_passthrough = deviceid_fullap[(deviceid_fullap['deviceId'].isin(virtual_deviceid) == False)
                                                    & (deviceid_fullap['fullAssetPath'].isin(virtual_fullap) == False)][['deviceId']].drop_duplicates()

        not_passthrough_data = self.entity_fields_data[[
            'deviceId', 'generalType', 'typeName']].drop_duplicates()
        reporting_not_passthrough = reporting_not_passthrough.merge(not_passthrough_data,
                                                                    how='left',
                                                                    on=['deviceId'],
                                                                    left_index=False,
                                                                    right_index=False)\
            .rename(columns={'generalType': 'dboGeneralType',
                             'typeName': 'dboEntityTypeName'})
        reporting_not_passthrough['isReporting'] = 'TRUE'
        reporting_not_passthrough['dboNamespace'] = 'HVAC'
        reporting_not_passthrough['etag'] = np.nan
        reporting_not_passthrough['cloudDeviceId'] = np.nan

        entities = pd.concat(
            [reporting_passthrough, reporting_not_passthrough, virtual_entities], axis=0)
        self.entity_data = entities

        self.LOADSHEET_IMPORTED = True

    def import_payload(self, path, format='csv'):
        """
        Import sample payload to pull available raw data values from.
        Args:
            path: path to sample payload file in json format.

        The payload file must be exported from PhRED nonconfidential entities table.
        Use the query below in Plx to get a discovery blob for all entities in the desired building, then copy the result in json format and save it in a separate .json file.
        set @building = 'US-SJC-TM2';
        with 
          discovery as (
            -- get latest discovery for all devices in the building
            select 
              a.Id,
              a.Timestamp,
              b.Payload
            from
            (select
              Id,
              max(Timestamp) as Timestamp
              from carson_users.discovery_results
              where RegistryName = @building
              group by Id) a
            left join carson_users.discovery_results b
            using(Id, Timestamp)
          ),
          entities as (
            -- get entities in the building
            select
              E.externalId.id as externalId,
              E.code as entity_code,
              E.guid as entity_guid,
              B.code as building,
              B.guid as building_guid 
            from phred_eng.non_confidential_entities_table E
            left join $phred.Connections C
            on E.EntityId = C.TargetEntityId
            left join phred_eng.non_confidential_entities_table B
            on C.SourceEntityId = B.EntityId and B.ExternalId.id like 'buildings%'
            where array_length(E.keys) <> 0
            and B.code = @building
            and E.code != ''
        ),
        final as (
          select 
            E.*,
            D.Timestamp as discovery_timestamp,
            D.Payload as discoveryresult     
            from entities E
            left join discovery D
            on E.externalId = D.Id
          and entity_code != ''
        )
        select * from final
        """

        def enumerate_fields(dataframe):
            enum = dataframe.sort_values(['reportingEntityGuid', 'standardFieldName', 'rawFieldName'])[['reportingEntityGuid', 'standardFieldName', 'rawFieldName']]\
                .drop_duplicates().reset_index(drop=True)
            enum['rawFieldName'] = enum['rawFieldName'].fillna('PLACEHOLDER')
            enum['fieldRank'] = enum.groupby(['reportingEntityGuid', 'standardFieldName'], as_index=False)['standardFieldName']\
                .rank(method="first", ascending=True, na_option='keep')
            enum['fieldCount'] = enum.groupby(['reportingEntityGuid', 'standardFieldName'], as_index=False)['standardFieldName']\
                .rank(method="max", ascending=True, na_option='keep')
            enum['fieldEnum'] = enum.apply(lambda x: '' if x['fieldCount'] == 1 else (
                '_'+str(int(x['fieldRank']))), axis=1)
            enum['reportingEntityField'] = enum['standardFieldName'] + \
                enum['fieldEnum']
            enum['rawFieldName'] = enum.apply(
                lambda x: np.nan if x['rawFieldName'] == 'PLACEHOLDER' else x['rawFieldName'], axis=1)

            dataframe = dataframe.merge(enum[['reportingEntityGuid', 'rawFieldName', 'standardFieldName', 'reportingEntityField']],
                                        how='left',
                                        on=['reportingEntityGuid',
                                            'rawFieldName', 'standardFieldName'],
                                        left_index=False,
                                        right_index=False)

            dataframe['fieldRankMissing'] = dataframe.groupby(['reportingEntityGuid', 'standardFieldName'], as_index=False)['standardFieldName']\
                .rank(method="first", ascending=True, na_option='keep')
            dataframe['fieldCountMissing'] = dataframe.groupby(['reportingEntityGuid', 'standardFieldName'], as_index=False)['standardFieldName']\
                .rank(method="max", ascending=True, na_option='keep')
            dataframe['fieldEnumMissing'] = dataframe.apply(
                lambda x: '' if x['fieldCountMissing'] == 1 else ('_'+str(int(x['fieldRankMissing']))), axis=1)

            # enumerate missing fields separately
            dataframe['reportingEntityField'] = dataframe.apply(lambda x: (x['reportingEntityField']+x['fieldEnumMissing'])
                                                                if x['rawFieldName'] is np.nan
                                                                else x['reportingEntityField'], axis=1)
            dataframe.drop(['fieldRankMissing', 'fieldCountMissing',
                           'fieldEnumMissing'], axis=1, inplace=True)

            return dataframe

        if format == 'json':
            f = open(path)
            entities = json.load(f)
            f.close()

            entities = entities[1:]

            self.site_code = entities[0][3]
            self.site_guid = entities[0][4]

            payload_data = []

            for cloud_id, entity_code, entity_guid, site_code, site_guid, payload in entities:
                data = json.loads(payload)
                device_id = data['device'].replace('bacnet-', 'DEV:')
                for key in data['data'].keys():
                    temp = {
                        'cloudDeviceId': cloud_id,
                        'entityCode': entity_code,  # same as controlProgram only from PhRED
                        'reportingEntityGuid': entity_guid,
                        'deviceId': device_id,
                        'rawFieldName': np.nan,
                        'objectName': np.nan,
                        'state': np.nan,
                        'rawUnitValue': np.nan
                    }

                    active = data['data'][key].get('active-text')
                    inactive = data['data'][key].get('inactive-text')
                    multi = data['data'][key].get(
                        'state-text') if data['data'][key].get('state-text') else np.nan
                    units = data['data'][key].get('units')

                    temp['rawFieldName'] = 'data.' + key + '.present-value'
                    temp['objectName'] = data['data'][key].get('object-name')
                    temp['state'] = [active, inactive] if all(
                        [active, inactive]) else multi
                    temp['rawUnitValue'] = units if units else 'no-units'

                    payload_data.append(temp)

            # , 'rawUnitValue']]\ # excluding raw values from payload for now bc they are not trustworthy and prevent exporting of a correct building config
            payload_df = pd.DataFrame.from_dict(payload_data)[['deviceId', 'rawFieldName', 'objectName', 'state']].rename(
                columns={'entityCode': 'reportingEntityCode'})

        if format == 'csv':
            def get_states(active, inactive, multi):
                return [active, inactive] if all([active, inactive]) else multi

            payload_data = pd.read_csv(path, dtype={'externalId': 'str'})
            payload_data = payload_data[payload_data['entity_code'].isna(
            ) == False]

            self.site_code = payload_data.loc[0, 'building']
            self.site_guid = payload_data.loc[0, 'building_guid']

            payload_data['discoveryresult'] = payload_data['discoveryresult'].apply(
                lambda x: json.loads(x))

            payload_data['rawFieldName'] = payload_data['discoveryresult'].apply(
                lambda x: list(x['data'].keys()))
            payload_data = payload_data.explode('rawFieldName')

            payload_data['data'] = payload_data.apply(
                lambda x: x['discoveryresult']['data'][x['rawFieldName']], axis=1)

            payload_data['objectName'] = payload_data.apply(
                lambda x: x['data'].get('object-name', np.nan), axis=1)
            # payload_data['rawUnitValue'] = payload_data.apply(lambda x: x['data'].get('units', 'no-units'), axis=1) # excluding raw values from payload for now bc they are not trustworthy and prevent exporting of a correct building config
            payload_data['state'] = payload_data.apply(lambda x: get_states(x['data'].get('active-text'),
                                                                            x['data'].get(
                                                                                'inactive-text'),
                                                                            x['data'].get('state-text', np.nan)), axis=1)

            payload_data['rawFieldName'] = payload_data['rawFieldName'].apply(
                lambda x: 'data.' + x + '.present-value')
            payload_data['deviceId'] = payload_data['discoveryresult'].apply(
                lambda x: x['device'].replace('bacnet-', 'DEV:'))
            payload_data = payload_data.rename(columns={'externalId': 'cloudDeviceId',
                                                        'entity_code': 'entityCode',
                                                        'entity_guid': 'reportingEntityGuid'
                                                        })
            payload_data.drop(['data', 'discoveryresult'],
                              axis=1, inplace=True)

            # , 'rawUnitValue']]
            payload_df = payload_data[['deviceId',
                                       'rawFieldName', 'objectName', 'state']]

        self.phred = payload_data[['deviceId', 'entityCode', 'cloudDeviceId', 'reportingEntityGuid']]\
            .drop_duplicates()\
            .rename(columns={
                'entityCode': 'phred_entityCode',
                'cloudDeviceId': 'phred_cloudDeviceId',
                'reportingEntityGuid': 'phred_reportingEntityGuid'
            })
        self.abel['PhRED'] = self.phred.to_dict()

        # CHECK DEVICES
        loadsheet_dev = self.entity_fields_data['deviceId'].unique().tolist()
        phred_dev = self.phred['deviceId'].unique().tolist()

        missing_dev = [dev for dev in loadsheet_dev if dev not in phred_dev]

        for dev in missing_dev:
            print((f'Required Device is missing in PhRED: {dev}'))
            self.log.append(f'Required device is missing in PhRED: {dev}')

        # CHECK OBJECTS
        loadsheet_obj = self.entity_fields_data[self.entity_fields_data['Missing'] == 'FALSE'][[
            'deviceId', 'rawFieldName']].drop_duplicates()
        loadsheet_obj['in_loadsheet'] = 'TRUE'
        phred_obj = payload_df[['deviceId', 'rawFieldName']].drop_duplicates()
        phred_obj['in_phred'] = 'TRUE'

        mismatch = loadsheet_obj.merge(phred_obj,
                                       how='left',
                                       on=['deviceId', 'rawFieldName'],
                                       left_index=False,
                                       right_index=False)

        mismatch = mismatch[mismatch['in_phred'].isna() == True].sort_values([
            'deviceId', 'rawFieldName'])

        for i in range(len(mismatch)):
            vals = mismatch.iloc[i]
            print(
                f'Required Object missing in PhRED: {vals.deviceId}, {vals.rawFieldName}')
            self.log.append(
                f'Required object missing in PhRED: {vals.deviceId}, {vals.rawFieldName}')

        #### UPDATE ENTITY DATA ###
        self.entity_data = self.entity_data.merge(self.phred,
                                                  how='left',
                                                  on=['deviceId'],
                                                  left_index=False,
                                                  right_index=False)
        self.entity_data['entityCode'] = self.entity_data.apply(
            lambda x: x['phred_entityCode'] if x['isReporting'] == 'TRUE' else x['entityCode'], axis=1)
        self.entity_data['cloudDeviceId'] = self.entity_data.apply(
            lambda x: x['phred_cloudDeviceId'] if x['isReporting'] == 'TRUE' else np.nan, axis=1)
        self.entity_data['entityGuid'] = self.entity_data.apply(
            lambda x: x['phred_reportingEntityGuid'] if x['isReporting'] == 'TRUE' else x['entityGuid'], axis=1)
        self.entity_data.drop(['phred_cloudDeviceId', 'phred_entityCode',
                              'phred_reportingEntityGuid'], axis=1, inplace=True)
        self.entity_data = self.entity_data[['entityCode', 'deviceId', 'entityGuid', 'etag',
                                             'isReporting', 'cloudDeviceId', 'dboNamespace', 'dboGeneralType', 'dboEntityTypeName']]

        #### UPDATE ENTITY FIELDS DATA ###
        self.entity_fields_data = self.entity_fields_data.merge(payload_df,
                                                                how='left',
                                                                on=['deviceId', 'rawFieldName',
                                                                    'objectName'],
                                                                left_index=False,
                                                                right_index=False)

        # Add Entity Guid, Reporting Entity Guid to Entity Fields
        entity_guids = self.entity_data[['entityCode', 'entityGuid']].drop_duplicates(
        ).rename(columns={'entityCode': 'fullAssetPath'})
        self.entity_fields_data = self.entity_fields_data.merge(entity_guids,
                                                                how='left',
                                                                on='fullAssetPath',
                                                                left_index=False,
                                                                right_index=False)

        # Add Reporting Entity Code and Reporting Entity Guid
        reporting_entity_data = self.phred[['deviceId', 'phred_entityCode', 'phred_reportingEntityGuid']]\
            .drop_duplicates()\
            .rename(columns={'phred_entityCode': 'reportingEntityCode',
                             'phred_reportingEntityGuid': 'reportingEntityGuid'})
        # Add Entity Code and Entity Guid
        self.entity_fields_data = self.entity_fields_data.merge(reporting_entity_data,
                                                                how='left',
                                                                on=['deviceId'],
                                                                left_index=False,
                                                                right_index=False)
        # fill in missing Entity Guids with placeholder to prevent error in enumeration
        self.entity_fields_data['reportingEntityGuid'] = self.entity_fields_data.apply(
            lambda x: 'MISSING IN PHRED:'+x['deviceId'] if x['reportingEntityGuid'] is np.nan else x['reportingEntityGuid'], axis=1)

        # Replace Entity Code with Reporting Entity Code in Entity Fields for non-modelled Entities:
        self.entity_fields_data['entityCode'] = self.entity_fields_data.apply(
            lambda x: x['reportingEntityCode'] if x['entityGuid'] is np.nan else x['fullAssetPath'], axis=1)

        # Enumerate fields by Reporting Entity Guid
        self.entity_fields_data = enumerate_fields(self.entity_fields_data)

        # Raw Unit Path, DBO Standard Unit Value, Raw Unit Value must be blank for binary and multi-state fields
        self.entity_fields_data.loc[(self.entity_fields_data['rawFieldName'].str.contains('binary') == True)
                                    | (self.entity_fields_data['rawFieldName'].str.contains('multi-state') == True), ['rawUnitPath', 'rawUnitValue', 'units']] = ''

        # ADD AND MAP STATES DATA

        def map_states(field_name, raw_state, mapper):
            try:
                return_value = mapper[field_name][raw_state.lower().strip()]
            except Exception:
                return_value = np.nan

            return (return_value)

        states = self.entity_fields_data.loc[(
            self.entity_fields_data['Missing'] == 'FALSE')]   # filter out missing points
        states = states.loc[(states['rawFieldName'].str.contains('binary') == True)
                            | (self.entity_fields_data['rawFieldName'].str.contains('multi-state') == True)][['reportingEntityCode', 'reportingEntityField', 'standardFieldName', 'state',
                                                                                                              'reportingEntityGuid']]           # get binary and multistate fields
        states = states.explode('state').sort_values(
            ['reportingEntityCode', 'reportingEntityField', 'state']).drop_duplicates()                   # flatten states
        states['dboStandardState'] = states.apply(lambda x: map_states(
            x['standardFieldName'], x['state'], value_mapping.STATES_BY_SFN), axis=1)   # map raw states to dbo standard states

        self.states_data = states.rename(columns={'state': 'rawState'})[
            ['reportingEntityCode', 'reportingEntityGuid', 'reportingEntityField', 'dboStandardState', 'rawState']]

        # Clear Reporting Entity Field for Reporting Entities that are not linked to any Virtual Entities (otherwise validation fails)
        self.entity_fields_data.loc[self.entity_fields_data['entityGuid'].isna(
        ) == True, 'reportingEntityField'] = np.nan

        self.PAYLOAD_IMPORTED = True

    def import_config(self, path):
        with open(path) as f:
            config = yaml.load(f, Loader=yaml.Loader)

        keys = [key for key in config.keys() if key != 'CONFIG_METADATA']

        entities = {}
        for key in keys:
            entities[key] = config[key]['etag']

        self.entity_data['etag'] = self.entity_data.apply(lambda x: entities.get(
            x['entityGuid'], np.nan) if x['isReporting'] == 'TRUE' else np.nan, axis=1)

    def dump(self, path):
        """
        Export ABEL formatted building config in excel format.
        Args: 
            path: path to the export file.
        """
        with pd.ExcelWriter(path) as writer:
            for key in list(self.abel.keys()):
                pd.DataFrame(self.abel[key]).to_excel(
                    writer, sheet_name=key, index=False)

    def build(self):
        """
        Builds config from the legacy loadsheet.
        """
        # Check for Entities wih missing data and add them to log :
        # Tbd
        # self.entity_fields_data.loc[self.entity_fields_data['controlProgram'].isna()==True]

        # Site
        self.abel['Site']['Building Code'] = [self.site_code] if self.site_code else list(
            self.entity_fields_data.building.unique())
        self.abel['Site']['Entity Guid'] = [self.site_guid] if self.site_guid else [
            ''] * len(self.entity_fields_data.building.unique())

        # Entity
        self.abel['Entities']['Entity Code'] = self.entity_data['entityCode']
        self.abel['Entities']['Entity Guid'] = self.entity_data['entityGuid']
        self.abel['Entities']['Etag'] = self.entity_data['etag']
        self.abel['Entities']['Is Reporting'] = self.entity_data['isReporting']
        self.abel['Entities']['Cloud Device ID'] = self.entity_data['cloudDeviceId']
        self.abel['Entities']['DBO Namespace'] = self.entity_data['dboNamespace']
        self.abel['Entities']['DBO General Type'] = self.entity_data['dboGeneralType']
        self.abel['Entities']['DBO Entity Type Name'] = self.entity_data['dboEntityTypeName']

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
        self.abel['Entity Fields']['DBO Standard Unit Value'] = self.entity_fields_data['units'].to_list()
        self.abel['Entity Fields']['Raw Unit Value'] = self.entity_fields_data['rawUnitValue'].tolist()

        # States
        self.abel['States']['Reporting Entity Code'] = self.states_data['reportingEntityCode'].to_list()
        self.abel['States']['Reporting Entity Guid'] = self.states_data['reportingEntityGuid'].to_list()
        self.abel['States']['Reporting Entity Field'] = self.states_data['reportingEntityField'].to_list()
        self.abel['States']['DBO Standard State'] = self.states_data['dboStandardState'].to_list()
        self.abel['States']['Raw State'] = self.states_data['rawState'].to_list()

        # Connections
        # TBD

        # Log
        self.abel['Log']['Index'] = [i+1 for i in range(len(self.log))]
        self.abel['Log']['Issue'] = self.log
