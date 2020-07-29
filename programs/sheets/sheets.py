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

from __future__ import print_function
import pickle, os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request


CREDS_FOLDER = '../resources/sheets/credentials.json'

class Sheets:
	def __init__(self,sheetId):
		self.credFolder = CREDS_FOLDER
		self.sheetId = sheetId
		self.sheetConn = None
		self.indexes = {}
		self.Connect()
		self.GetSheetMetadata()


	def connect(self):
		""" Create the connection to Sheets. """

		scopes = ['https://www.googleapis.com/auth/spreadsheets']
		creds = None
		if os.path.exists(self.credFolder + '/token.pickle'):
		    with open(self.credFolder +'/token.pickle', 'rb') as token:
		        creds = pickle.load(token)
		# If there are no (valid) credentials available, let the user log in.
		if not creds or not creds.valid:
		    if creds and creds.expired and creds.refresh_token:
		        creds.refresh(Request())
		    else:
		        flow = InstalledAppFlow.from_client_secrets_file(
		            self.credFolder + '/credentials.json', scopes)
		        creds = flow.run_local_server()
		    # Save the credentials for the next run
		    with open(self.credFolder +'/token.pickle', 'wb') as token:
		        pickle.dump(creds, token)
		self.sheetConn = build('sheets', 'v4', credentials=creds).spreadsheets()

	def get_sheet_metadata(self):
		""" Get sheet names and indexes. """
		sheetMetadata = self.sheetConn.get(spreadsheetId=self.sheetId).execute()
		metadata = sheetMetadata.get('sheets', '')
		self.indexes = {}
		for sheet in metadata:
			self.indexes[sheet['properties']['title']] = sheet['properties']['sheetId']

	def create_sheet(self,sheetName):
		""" Create sheet with given name. """
		self.get_sheet_metadata()
		if sheetName not in self.indexes:
			request = {'addSheet':{
				'properties':{
				  "title": sheetName,
				  "index": 1,
				  "sheetType": "GRID",
				  "hidden": False
					}
				}
			}
			body = {'requests': [request]}
			response = self.sheetConn.batchUpdate(spreadsheetId=self.sheetId,body=body).execute()
			self.get_sheet_metadata()
			return response
		else:
			print('SHEET ALREADY EXISTS!')

	def delete_sheet(self,sheetName):
		""" Delete sheet with a given name. """
		self.get_sheet_metadata()
		if sheetName in self.indexes:
			request = {'deleteSheet':{'sheetId':self.indexes[sheetName]}}
			body = {'requests': [request]}
			response = self.sheetConn.batchUpdate(spreadsheetId=self.sheetId,body=body).execute()
			self.get_sheet_metadata()
			return response
		else:
			print("SHEET DOESN'T EXIST!")

	def find_replace(self,find,replace,sheetName):
		""" Find and replace data in a sheet or sheets. """
		if sheetName in self.indexes:
			request = {
			    'findReplace': {
			        'find': find,
			        'replacement': replace,
			        'sheetId': self.indexes[sheetName]
			    }
			}
			body = {'requests': [request]}
			response = self.sheetConn.batchUpdate(spreadsheetId=self.sheetId,body=body).execute()
			return response
		else:
			print("SHEET DOESN'T EXIST!")

	def load_to_new_sheet(self,data,sheetName):
		""" Load data into a sheet. """

		def get_letter(number):
			""" Convert a number to alphabetic list (spreadsheet column style). """
			assert number > 0, 'NUMBER NEEDS TO BE GREATER THAN 0'
			assert type(number) == int, 'NUMBER ISNT A NUMBER'
			letters = ['A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P','Q','R','S','T','U','V','W','X','Y','Z']
			ls = []
			def get_vals(number):
				i = int(number/26)
				r = number%26
				return i,r
			i, r = get_vals(number)
			if i == 0:
				ls.append(letters[r-1])
			elif i <= 26:
				ls.append(letters[i-1])
				ls.append(letters[r-1])
			else:
				ls.append(get_letter(i))
				ls.append(letters[r-1])
			return ''.join(ls)

		rows = data['rows']
		cols = data['cols']

		if sheetName in self.indexes:
			self.delete_sheet(sheetName)
			self.create_sheet(sheetName)
		else:
			self.create_sheet(sheetName)

		rangeStr = sheetName + '!A1:'+get_letter(cols)+str(rows+1)
		body = {'values': data['data']}
		result = self.sheetConn.values().update(spreadsheetId=self.sheetId,range=rangeStr,valueInputOption='RAW',body=body).execute()
		return result

	def get_sheet_data(self,sheetRange=None):
		""" Read data from a sheet range. """
		result = self.sheetConn.values().get(
			spreadsheetId=self.sheetId,
			range=sheetRange).execute()
		return result
