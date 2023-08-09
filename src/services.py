"""
services.py

This module is responsible for initializing and configuring various services
used by the application.
Currently, it initializes and configures the following services:

- `sheet`: An instance of the `GoogleSheets` class from the `gsheets` module,
           configured with the Google application credentials and the
           spreadsheet ID from the `constants` module.
- `twitch`: An instance of the `Twitch` class from the `twitch` module,
            configured with the Twitch client ID, client secret, callback URL,
            and hub secret from the `constants` module.
- `twitch_handler`: An instance of the `TwitchHandler` class from the `twitch`
                    module, configured with the `twitch` instance from this
                    module.

These services can be imported into other modules where needed, reducing the
clutter in the global namespace and making it easier to manage these shared resources.
"""


import logging
from googlesheets import SheetManager
from twitch import Twitch, TwitchHandler
import constants


logger = logging.getLogger(__name__)


def configure_services():
    """
    Initializes and configures the application services.
    
    This function attempts to initialize the following services: GoogleSheets,
    Twitch, and TwitchHandler. If an error occurs during the initialization of a
    service, an error message is logged and the corresponding service variable is
    set to None.
    
    Returns:
        tuple: A tuple containing the initialized services. The services are returned
               in the following order: GoogleSheets, Twitch, TwitchHandler. If a
               service fails to initialize, its corresponding value in the tuple
               will be None.
    """

    sheet_mgr = None
    twitch = None
    twitch_handler = None

    try:
        sheet_mgr = SheetManager(
            constants.GOOGLE_APPLICATION_CREDENTIALS,
            constants.REF_SPREADSHEET_ID)
    except FileNotFoundError as file_error:
        print(f"Failed to initialize GoogleSheets: {file_error}")

    try:
        twitch = Twitch()
    except ValueError as value_error:
        print(f"Failed to initialize Twitch: {value_error}")

    try:
        twitch_handler = TwitchHandler()
    except ValueError as value_error:
        print(f"Failed to initialize TwitchHandler: {value_error}")

    return sheet_mgr, twitch, twitch_handler
