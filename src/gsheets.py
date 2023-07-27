"""
gsheets.py

This module provides the GoogleSheets class, an interface for interacting with
a specific Google Sheet.
The GoogleSheets class uses the Google Sheets API to fetch, append, and update
rows of data in the Google Sheet.

The class provides functionality for:
- Retrieving all rows from the sheet.
- Appending a new row to the sheet.
- Updating an existing row in the sheet.
- Getting the row number for a specific user based on their user ID.

Example usage:
    sheet = GoogleSheets(service_account_file_path, spreadsheet_id)
    all_rows = sheet.get_all_rows()
    sheet.append_or_update_row(user_id, user_name, gifted_subs, rewards_given)

This module requires the `google-auth` and `google-api-python-client` packages.
"""

import logging
from typing import List, Dict, Optional
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.exceptions import RefreshError, TransportError


class GoogleSheets:
    """
    A class for interacting with Google Sheets using the Google Sheets API.

    This class provides methods to append or update rows in a Google Sheet
    and to retrieve all rows from the sheet.
    """

    def __init__(self, service_acct_file: str, spreadsheet_id: str):
        """
        Initializes the GoogleSheets class.

        Args:
            service_acct_file (str): The path to the service account key file.
            spreadsheet_id (str): The ID of the Google Sheet to interact with.
        """

        self.spreadsheet_id = spreadsheet_id
        self.scopes = ['https://www.googleapis.com/auth/spreadsheets']
        self.schema = ['user_id', 'user_name', 'gifted_subs', 'rewards_given']
        self.logger = logging.getLogger(__name__)

        # Load the service account credentials
        try:
            creds = Credentials.from_service_account_file(
                service_acct_file, scopes=self.scopes)
            self.service = build('sheets', 'v4', credentials=creds)
            self.sheet = self.service.spreadsheets()
        except Exception as credential_error:
            self.logger.error(
                "Failed to build Google Sheets service: %s", credential_error)
            raise

    def get_user_row(self, user_id: str) -> Optional[int]:
        """
        Gets the row number for a user based on their user_id.

        Args:
            user_id (str): The user_id to search for.

        Returns:
            The row number of the user, or None if the user was not found.
            Note: Rows in Google Sheets are 1-indexed, but in the Google Sheets
                API, row indices are 0-indexed.
        """

        result = self.sheet.values().get(
            spreadsheetId=self.spreadsheet_id, range='Sheet1').execute()
        values = result.get('values', [])
        for i, row in enumerate(values):
            if row[0] == str(user_id):
                return i + 1  # Rows are 1-indexed in Google Sheets
        return None

    def append_or_update_row(self,
                             user_id: str,
                             user_name: str,
                             gifted_subs: int,
                             rewards_given: int):
        """
        Appends a new row to the Google Sheet or updates an existing row.

        If a row with the given user_id exists, this method updates the row
        with the new data. Otherwise, it appends a new row with the given data.

        Args:
            user_id (str): The user_id of the user.
            user_name (str): The user_name of the user.
            gifted_subs (int): The number of gifted_subs for the user.
            rewards_given (int): The number of rewards_given for the user.
        """

        try:
            row = self.get_user_row(user_id)
            if row is None:
                # User not found, append a new row
                values = [[user_id, user_name, gifted_subs, rewards_given]]
                body = {'values': values}
                result = self.sheet.values().append(
                    spreadsheetId=self.spreadsheet_id,
                    range='Sheet1',
                    valueInputOption='USER_ENTERED',
                    body=body).execute()
                self.logger.info("Appended %s cells.", result.get(
                    'updates').get('updatedCells'))

            else:
                # User found, update the existing row
                result = self.sheet.values().get(
                    spreadsheetId=self.spreadsheet_id,
                    range=f'Sheet1!A{row}:D{row}').execute()
                values = result.get('values', [])
                if values:
                    # Create a dictionary for easier access to values
                    row_values = dict(zip(self.schema, values[0]))
                    # Add the new gifted_subs to the existing gifted_subs
                    gifted_subs += int(row_values['gifted_subs'])
                    # Increment the rewards_given by the given amount
                    rewards_given += int(row_values['rewards_given'])

                values = [[user_id, user_name, gifted_subs, rewards_given]]
                body = {'values': values}
                result = self.sheet.values().update(
                    spreadsheetId=self.spreadsheet_id,
                    range=f'Sheet1!A{row}:D{row}',
                    valueInputOption='USER_ENTERED',
                    body=body).execute()
                self.logger.info("Updated %s cells.",
                                 result.get('updatedCells'))

        except HttpError as http_error:
            self.logger.error("Failed to append or update row: %s", http_error)
            raise

        except (RefreshError, TransportError) as auth_error:
            self.logger.error(
                "Google Sheets API connection error: %s", auth_error)
            raise

        except Exception as general_error:
            self.logger.error(
                "Unexpected error in append_or_update_row: %s", general_error)
            raise

    def get_all_rows(self) -> List[Dict[str, int]]:
        """
        Retrieves all rows from the Google Sheet, excluding the header row.

        Returns:
            A list of dictionaries, where each dictionary represents a row in the sheet.
            Each dictionary has keys 'user_id', 'user_name', 'gifted_subs', and 'rewards_given'.
        """

        try:
            result = self.sheet.values().get(
                spreadsheetId=self.spreadsheet_id, range='Sheet1').execute()
            values = result.get('values', [])
            rows = []
            for row_values in values[1:]:  # Skip the header row
                row = dict(zip(self.schema, [row_values[0], row_values[1], int(
                    row_values[2]), int(row_values[3])]))
                rows.append(row)
            return rows
        except HttpError as http_error:
            self.logger.error("Failed to get all rows: %s", http_error)
            raise
        except (RefreshError, TransportError) as auth_error:
            self.logger.error(
                "Google Sheets API connection error: %s", auth_error)
            raise
        except Exception as general_error:
            self.logger.error(
                "Unexpected error in get_all_rows: %s", general_error)
            raise
