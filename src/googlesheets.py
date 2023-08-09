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

from googleapiclient.discovery import build
from google.oauth2 import service_account
import constants


class GoogleSheets:
    """
    A class for interacting with Google Sheets using the Google Sheets API.

    This class provides methods to append or update rows in a Google Sheet
    and to retrieve all rows from the sheet.
    """

    def __init__(self, credentials_path: str, spreadsheet_id: str):
        self.credentials_path = credentials_path
        self.spreadsheet_id = spreadsheet_id
        self.sheet_service = self._authenticate()
        self.schema = []  # Overwrite in children classes

    def _get_headers(self):
        """
        Retrieves the headers from the Google Sheet.

        Returns:
            headers (list): The headers of the Google Sheet.
        """
        rows = self.get_all_rows(include_headers=True)
        if rows:
            return list(rows[0].keys())
        else:
            return []

    def _validate_schema(self):
        """
        Validates that the Google Sheet conforms to the expected schema.

        Raises:
            ValueError: If the Google Sheet does not conform to the expected schema.
        """
        headers = self._get_headers()
        if headers != self.schema:
            raise ValueError('The Google Sheet does not conform to the expected schema.' +
                             f'Expected: {self.schema}, but got: {headers}')

    def _authenticate(self):
        """Authenticate to Google API using OAuth 2.0

        This method will try to authenticate using saved token.pickle file,
        if it does not exist, it will open a new window for user to authenticate.

        Returns:
            service: a Resource object with methods for interacting with the service.
        """

        # Load the credentials from the service account file
        creds = service_account.Credentials.from_service_account_file(
            self.credentials_path,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )

        # Build the Sheets API service
        service = build('sheets', 'v4', credentials=creds)

        return service

    def _column_index_to_letter(self, column_id):
        """
        Converts a 0-based column index into a column letter.

        Args:
            column_id (int): The 0-based column index.

        Returns:
            str: The corresponding column letter.
        """
        return chr(65 + column_id)

    def get_all_rows(self, include_headers=False):
        """
        Retrieves all rows from the Google Sheet.

        Args:
            include_headers (bool): Whether to include the header row in the returned list.

        Returns:
            rows: A list of dictionaries representing each row in the sheet.
        """
        # Request all data from the sheet
        result = self.sheet_service.spreadsheets().values().get(
            spreadsheetId=self.spreadsheet_id,
            range="A1:Z1000").execute()

        # Get the values from the response
        values = result.get('values', [])

        if len(values) == 0:
            return []

        # Get the headers (first row) and the rest of the data
        headers, data = values[0], values[1:]

        # Convert the data to a list of dictionaries (one dictionary per row)
        rows = [dict(zip(headers, row)) for row in data]

        if include_headers:
            # Include the header row at the start of the list
            headers_row = {header: header for header in headers}
            rows.insert(0, headers_row)

        return rows

    def find_row_by_col_value(self, column_name: str, value: str):
        """
        Finds a row in the Google Sheet where the specified column matches the
        specified value.

        Args:
            column_name (str): The name of the column to search, must match the
                schema's name.
            value (str): The value to match in the specified column.

        Returns:
            row (dict): A dictionary representing the row where the column
                matches the value.
        """
        # Retrieve all rows from the sheet
        rows = self.get_all_rows()

        # Determine the column identifier
        col_id = self.schema.index(column_name)
        col_letter = self._column_index_to_letter(col_id)

        # Find the first row where the specified column matches the value
        for row in rows:
            if row.get(col_letter) == value:
                return row

        # If no match is found, return None
        return None

    def update_cell(self, cell_address: str, new_value: str):
        """
        Updates a specified cell with a new value.

        Args:
            cell_address (str): The address of the cell to update (e.g., 'A1').
            new_value (str): The new value to set in the cell.
        """
        # Prepare the new value
        value_range_body = {
            "values": [[new_value]]
        }

        # Update the cell
        self.sheet_service.spreadsheets().values().update(
            spreadsheetId=self.spreadsheet_id,
            range=cell_address,
            valueInputOption="USER_ENTERED",
            body=value_range_body
        ).execute()

    def append_or_update_row(self, values_dict: dict):
        """
        Searches for row in the spreadsheet. If found, updates it with the
        provided values. If not, appends the row to the end of the spreadsheet.

        Args:
            values_dict(dict): A dictionary, keys match the columns, values
                will be written to the corresponding cells.
        Returns:
            None
        """
        if set(values_dict.keys()) != set(self.schema):
            raise ValueError('values_dict keys do not match the schema of the sheet.')

        # Use the first item in the schema as the key to find the row
        key = self.schema[0]
        value = values_dict[key]

        row = self.find_row_by_col_value(key, value)

        if row is not None:
            # If the row is found, update the cells with the new values
            for column_index, column_name in enumerate(self.schema):
                new_value = values_dict[column_name]
                # Calculate the letter of the column
                column_id = chr(constants.UNICODE_A_VALUE + column_index)
                cell_address = f"{column_id}{row['row_number']}"
                self.update_cell(cell_address, new_value)
        else:
            # If the row is not found, append a new row to the end of the sheet
            row_values = [values_dict[column_name] for column_name in self.schema]
            value_range_body = {
                "values": [row_values]
            }
            new_row_index = len(self.get_all_rows()) + 2
            self.sheet_service.spreadsheets().values().append(
                spreadsheetId=self.spreadsheet_id,
                range=f"A{new_row_index}:Z{new_row_index}",
                valueInputOption="USER_ENTERED",
                body=value_range_body
            ).execute()


class ReferenceSheet(GoogleSheets):
    """
    Represents a Google Sheet with a schema of (user_id, spreadsheet_id).

    This class is used to interact with a specific type of Google Sheet that stores reference data.
    The Google Sheet is expected to have two columns: 'user_id' and 'spreadsheet_id'.

    Attributes:
        credentials_path (str): The path to the service account credentials file.
        spreadsheet_id (str): The ID of the Google Sheet.
        schema (list): The expected schema of the Google Sheet.
        sheet_service (Resource): The authenticated Sheets API service.

    Methods:
        __init__(self, credentials_path: str, spreadsheet_id: str): Initialize
            a ReferenceSheet instance.
    """

    def __init__(self, credentials_path, spreadsheet_id):
        super().__init__(credentials_path, spreadsheet_id)
        self.schema = ['user_id', 'sheet_id']
        self._validate_schema()


class StreamerSheet(GoogleSheets):
    """
    Represents a Google Sheet with a schema of (user_id, user_name, gifted_subs, rewards_given).

    This class is used to interact with a specific type of Google Sheet that stores streamer data.
    The Google Sheet is expected to have four columns: 'user_id', 'user_name', 'gifted_subs', and
    'rewards_given'.

    Attributes:
        credentials_path (str): The path to the service account credentials file.
        spreadsheet_id (str): The ID of the Google Sheet.
        schema (list): The expected schema of the Google Sheet.
        sheet_service (Resource): The authenticated Sheets API service.

    Methods:
        __init__(self, credentials_path: str, spreadsheet_id: str): Initializes a StreamerSheet
            instance.
    """

    def __init__(self, credentials_path: str, spreadsheet_id: str):
        super().__init__(credentials_path, spreadsheet_id)
        self.schema = ['user_id', 'user_name', 'gifted_subs', 'rewards_given']
        self._validate_schema()

    def increment_rewards_given(self, user_id: str):
        """
        Increments the rewards_given value for a specific user.

        Args:
            user_id (str): The user_id to look up.

        Returns:
            int: The new rewards_given value, or None if the user_id is not found.
        """
        row = self.find_row_by_col_value('user_id', user_id)

        if row is not None:
            # Get the current rewards_given value
            rewards_given = row['rewards_given']
            # Increment the rewards_given value
            rewards_given += 1
            # Update the cell with the new value
            cell_address = f"rewards_given{row['row_number']}"
            self.update_cell(cell_address, rewards_given)

            return rewards_given

        # Return None if the user_id is not found
        return None


class SheetManager:
    """
    Maps user_ids to StreamerSheet instances based on data from a ReferenceSheet.

    This class is used to generate and store a mapping of user_ids to StreamerSheet instances.
    The mapping is based on data from a ReferenceSheet, which contains user_ids and corresponding
    spreadsheet_ids.
    The spreadsheet_ids are used to initialize the StreamerSheet instances.

    Attributes:
        reference_sheet (ReferenceSheet): A ReferenceSheet instance that contains the mapping data.
        streamer_sheets (dict): A dictionary that maps user_ids to StreamerSheet instances.

    Methods:
        __init__(self, credentials_path: str, reference_spreadsheet_id: str): Initializes a
            StreamerSheetMapper instance.
        generate_map(self): Generates a dictionary mapping user_ids to StreamerSheet instances.
        get_streamer_sheet(self, user_id: str): Retrieves the StreamerSheet instance for a specific
            user.
    """

    def __init__(self, credentials_path: str, reference_spreadsheet_id: str):
        """
        Initializes a StreamerSheetMapper instance.

        Args:
            credentials_path (str): The path to the service account credentials file.
            reference_spreadsheet_id (str): The ID of the ReferenceSheet.
        """
        self.credentials_path = credentials_path
        self.reference_sheet = self._create_ref_sheet(reference_spreadsheet_id)
        self.streamer_sheets = self._generate_map()
        self.drive_service = self._authenticate_drive()

    def _authenticate_drive(self):
        """
        Authenticates the Google Drive API using a service account credentials file.
        
        Returns:
            service: An authorized Drive API service instance.
        """
        creds = service_account.Credentials.from_service_account_file(
            self.credentials_path,
            scopes=['https://www.googleapis.com/auth/drive']
        )
        service = build('drive', 'v3', credentials=creds)
        return service

    def _create_ref_sheet(self, reference_sheet_id: str):
        """Creates an instance of a ReferenceSheet object.
        
        Args:
            reference_sheet_id(str): The ID of the GoogleSheet that holds the
                """
        return ReferenceSheet(self.credentials_path, reference_sheet_id)

    def _create_streamer_sheet(self, user_id: str):
        """
        Creates a new Google Sheet for a new user.

        Args:
            user_id (str): The user_id of the new user.

        Returns:
            spreadsheet_id (str): The ID of the newly created Google Sheet.
        """
        print(f"create_streamer_sheet() called for {user_id}")
        # Create a new Google Sheet
        sheet = self.drive_service.files().create(body={
            'name': f'{user_id}_sheet',
            'mimeType': 'application/vnd.google-apps.spreadsheet'
        }).execute()

        # Get the new spreadsheet_id
        spreadsheet_id = sheet['id']

        # Calculate new row number.
        # Python arrays are zero-indexed, while GoogleSheets are 1-indexed.
        row_number = len(self.streamer_sheets) + 2
        # Add the new user_id and spreadsheet_id to the reference sheet
        self.reference_sheet.update_cell(f'A{row_number}', user_id)
        self.reference_sheet.update_cell(f'B{row_number}', spreadsheet_id)

        # Add a new StreamerSheet instance to the map
        self.streamer_sheets[user_id] = StreamerSheet(self.credentials_path, spreadsheet_id)

        return spreadsheet_id

    def _generate_map(self) -> dict:
        """
        Reads the ReferenceSheet and generates a dictionary mapping user_ids to
        StreamerSheet instances.

        Returns:
            streamer_sheets (dict): A dictionary mapping user_ids to
                StreamerSheet instances.
        """
        streamer_sheets = {}

        # Retrieve all rows from the reference sheet
        rows = self.reference_sheet.get_all_rows()

        # Create a StreamerSheet instance for each row and add it to the map
        for row in rows:
            print(f"Row: {row}")
            user_id = row['user_id']
            spreadsheet_id = row['sheet_id']
            streamer_sheets[user_id] = StreamerSheet(
                self.reference_sheet.credentials_path,
                spreadsheet_id)

        return streamer_sheets

    def get_ref_sheet(self):
        """Returns a reference sheet object.
        
        Returns:
            A ReferenceSheet object."""

        return self.reference_sheet

    def get_streamer_sheet(self, user_id: str) -> StreamerSheet:
        """
        Retrieves the StreamerSheet instance for a specific user, if a sheet
        doesn't exist it creates a new one.

        Args:
            user_id (str): The user_id to look up.

        Returns:
            streamer_sheet (StreamerSheet): The StreamerSheet instance for the specified user.
        """
        streamer_sheet_obj = self.streamer_sheets.get(user_id, None)
        if streamer_sheet_obj is None:
            streamer_sheet_obj = self._create_streamer_sheet(user_id)
        return streamer_sheet_obj

    def get_streamer_rows(self, user_id: str) -> list:
        """
        Retrieves all the rows from a streamer's spreadsheet.

        Args:
            user_id(str): The user ID of the streamer.

        Returns:
            A list of dictionaries, each one representing a row of the
            spreadsheet.
        """
        print("get_streamer_rows()")
        self._generate_map()
        streamer_sheet = self.streamer_sheets.get(user_id)
        print(user_id)
        if streamer_sheet is None:
            streamer_sheet = self._create_streamer_sheet(user_id)
        return streamer_sheet
