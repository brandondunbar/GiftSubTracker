"""
webhook_handler.py

This module contains the WebhookHandler class, responsible for managing incoming 
Events from the Twitch API. These events include subscription notifications and
other interactions with the Twitch platform. Upon receiving an event, the
WebhookHandler class processes the event data, updates a Google Sheets document
with the relevant information, and communicates the event data to a SocketIO
server for real-time updates.
"""


from typing import Dict, Union
from flask_socketio import SocketIO
from googlesheets import StreamerSheet


class WebhookHandler:
    """
    Handles incoming requests to the Twitch webhook and updates the Google sheet
    and SocketIO server accordingly.

    Attributes:
        sheet (GoogleSheets): The Google Sheets object for interacting with the spreadsheet.
        socketio (SocketIO): The SocketIO server for real-time updates.
    """

    def __init__(self, sheet: StreamerSheet, socketio: SocketIO) -> None:
        """
        Constructs the necessary attributes for the WebhookHandler object.

        Args:
            sheet (GoogleSheets): The Google Sheets object for interacting with the spreadsheet.
            socketio (SocketIO): The SocketIO server for real-time updates.
        """

        self.sheet = sheet
        self.socketio = socketio

    def handle_webhook(self, data: Dict[str, Union[str, Dict[str, Union[str, int]]]]) -> str:
        """
        Processes incoming requests to the Twitch webhook. If the request is a subscription
        verification, it returns the challenge. Otherwise, it updates the Google sheet and
        SocketIO server with the gifted subs information.

        Args:
            data (dict): The request data.

        Returns:
            str: 'OK' if the request is handled successfully, or the challenge string if the
            request is a subscription verification.
        """

        # Check if this is a subscription verification request
        if 'challenge' in data:
            return data['challenge']

        updates = {
            'user_id': data['event']['user_id'],
            'user_name': data['event']['user_name'],
            'gifted_subs': data['event']['total'],
            'rewards_given': 0
        }

        self.socketio.emit('update_gifters', updates)
        self.sheet.append_or_update_row(updates)

        return 'OK'
