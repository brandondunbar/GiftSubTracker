"""
twitch.py

This module provides two classes, Twitch and TwitchHandler, for interacting with Twitch's API.

The Twitch class provides methods for the following operations:
    - Verifying and setting user access tokens.
    - Getting an authorization URL for a user to grant permissions to the application.
    - Requesting a user access token, given an authorization code.
    - Getting an app access token for making API requests.
    - Retrieving the Twitch username and broadcaster ID associated with a user access token.
    - Subscribing to Twitch's EventSub system for real-time notifications of events.

The TwitchHandler class is a higher-level interface that creates a Twitch instance to handle
webhook verification and user authorization.

Example:
    twitch_handler = TwitchHandler(client_id, client_secret, callback_url, secret)
    access_token = twitch_handler.handle_verification(auth_code)
    auth_url = twitch_handler.handle_authorization()

This module requires the `requests` package.
"""

import logging
import json
from urllib.parse import urlencode
from enum import Enum
import requests
import constants
import hashlib
import hmac


class URLs(Enum):
    """
    Holds the URLs relevant to using the Twitch API.
    """
    VALIDATE = 'https://id.twitch.tv/oauth2/validate'
    AUTHORIZE = 'https://id.twitch.tv/oauth2/authorize'
    TOKEN = 'https://id.twitch.tv/oauth2/token'
    USERS = 'https://api.twitch.tv/helix/users'
    SUBSCRIPTIONS = 'https://api.twitch.tv/helix/eventsub/subscriptions'


class Twitch:
    """
    A class for interacting with Twitch's API.
    """

    def __init__(self, http_service=None):
        """
        Initializes a Twitch instance.

        Args:
            http_service (requests.Session, optional): An HTTP service for making requests.
                Defaults to the `requests` package's main session.
        """

        # If no HTTP service is provided, use requests
        self.http_service = http_service if http_service else requests

        # Set up logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

        self.credentials = {
            'client_id': constants.TWITCH_CLIENT_ID,
            'client_secret': constants.TWITCH_CLIENT_SECRET,
            'callback_url': f"{constants.DOMAIN_NAME}/webhook",
            'secret': constants.TWITCH_HUB_SECRET
        }
        self.auth_code = None
        self.user_access_token = None
        self.app_access_token = self.get_app_access_token()
        self.broadcaster_id = None

    def set_user_access_token_if_valid(self, token: str) -> bool:
        """
        Sets the user access token if the given token is valid.

        Args:
            token (str): The token to validate and set.

        Returns:
            bool: True if the token is valid, False otherwise.
        """

        valid = self.is_access_token_valid(token)
        self.user_access_token = token if valid else self.user_access_token
        return valid

    def is_access_token_valid(self, token: str) -> bool:
        """
        Checks if a given access token is valid.

        Args:
            token (str): The token to validate.

        Returns:
            bool: True if the token is valid, False otherwise.
        """

        headers = {'Authorization': f'Bearer {token}'}
        response = self.make_request(URLs.VALIDATE.value, headers=headers)

        return response.status_code == 200

    def get_auth_url(self) -> str:
        """
        Constructs and returns a Twitch authorization URL.

        Returns:
            str: The Twitch authorization URL.
        """

        params = {
            'client_id': self.credentials['client_id'],
            'redirect_uri': self.credentials['callback_url'],
            'response_type': 'code',
            'scope': 'channel:read:subscriptions'
        }

        url = URLs.AUTHORIZE.value + "?" + urlencode(params)

        return url

    def get_user_access_token(self) -> str:
        """
        Returns the user access token.

        Returns:
            str: The user access token.
        """

        return self.user_access_token

    def request_user_access_token(self, code: str):
        """
        Requests a user access token using an authorization code.

        Args:
            code (str): The authorization code.

        Returns:
            str: The user access token.
        """

        params = {
            'client_id': self.credentials['client_id'],
            'client_secret': self.credentials['client_secret'],
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': self.credentials['callback_url']
        }

        response = self.make_request(
            URLs.TOKEN.value, params=params, method="POST")
        data = response.json()

        self.user_access_token = data['access_token']

    def get_app_access_token(self) -> str:
        """
        Requests and returns an app access token.

        Returns:
            str: The app access token.
        """
        params = {
            'client_id': self.credentials['client_id'],
            'client_secret': self.credentials['client_secret'],
            'grant_type': 'client_credentials'
        }

        response = self.make_request(
            URLs.TOKEN.value, params=params, method="POST")
        
        if not response:
            raise RuntimeError("Failed to get app access token.")

        data = response.json()
        return data['access_token']

    def get_user_name(self):
        """
        Returns the Twitch username associated with the user access token.

        Returns:
            str: The Twitch username.
        """

        headers = {
            'Client-ID': self.credentials['client_id'],
            'Authorization': f'Bearer {self.user_access_token}'
        }

        response = self.make_request(URLs.USERS.value, headers=headers)

        if not response:
            raise RuntimeError("Failed to get Twitch username.")

        data = response.json()

        if data['data']:
            return data['data'][0]['login']
        
        raise RuntimeError(f'Failed to get Twitch username: {response.text}')

    def get_broadcaster_id(self):
        """
        Returns the broadcaster ID associated with the Twitch username.

        Returns:
            str: The broadcaster ID.
        """

        user_name = self.get_user_name()

        headers = {
            'Client-ID': self.credentials['client_id'],
            'Authorization': f'Bearer {self.user_access_token}'
        }

        response = self.make_request(
            URLs.USERS.value + f"?login={user_name}", headers=headers)

        data = response.json()['data']
        if data:
            self.broadcaster_id = data[0]['id']
            return self.broadcaster_id
        else:
            self.logger.error('No broadcaster found with name %s', user_name)
            return None

    def subscribe_to_eventsub(self):
        """
        Subscribes to the `channel.subscription.gift` event on Twitch's EventSub system.

        Returns:
            bool: True if the subscription was successful, False otherwise.
        """

        headers = {
            'Client-ID': self.credentials['client_id'],
            'Authorization': f'Bearer {self.app_access_token}',
            'Content-Type': 'application/json'
        }

        payload = {
            'type': 'channel.subscription.gift',
            'version': '1',
            'condition': {
                'broadcaster_user_id': self.broadcaster_id
            },
            'transport': {
                'method': 'webhook',
                'callback': self.credentials['callback_url'],
                'secret': self.credentials['secret']
            }
        }

        response = self.make_request(
            URLs.SUBSCRIPTIONS.value, headers=headers, data=json.dumps(payload), method="POST")

        if response is not None and response.status_code == 200:
            self.logger.info('EventSub subscription successful')
            return True

        self.logger.error('EventSub subscription failed')
        return False

    def make_request(self, url, headers=None, params=None, data=None, method="GET"):
        """
        Wrapper method for making HTTP requests with error handling.

        Args:
            url (str): The URL to make the request to.
            headers (dict, optional): Headers to include in the request.
            params (dict, optional): Parameters to include in the request.
            data (str, optional): Data to include in the request.
            method (str, optional): HTTP method to use for the request.

        Returns:
            requests.Response: The response from the server.
        """

        try:
            if method == "GET":
                response = self.http_service.get(
                    url, headers=headers, params=params, timeout=5)
            elif method == "POST":
                response = self.http_service.post(
                    url, headers=headers, params=params, data=data, timeout=5)

            response.raise_for_status()
            self.logger.info('Successful %s request to %s', method, url)
            return response

        except requests.RequestException as request_error:
            self.logger.error("Failed %s request to %s: %s",
                              method, url, request_error)

            return None


class TwitchHandler:
    """
    A class for handling Twitch webhook verification and user authorization.
    """

    def __init__(self, http_service=None):
        """
        Initializes a TwitchHandler instance.
        """
        self.twitch = Twitch(http_service)

    def handle_verification(self, auth_code):
        """
        Handles the verification process for a Twitch webhook.

        Args:
            auth_code (str): The authorization code.

        Returns:
            str: The user access token.
        """
        try:
            self.twitch.request_user_access_token(auth_code)
            self.twitch.get_broadcaster_id()
            self.twitch.subscribe_to_eventsub()
        except Exception as request_error:
            self.twitch.logger.error("Failed to handle verification: %s", str(request_error))
            raise

        return self.twitch.get_user_access_token()

    def handle_authorization(self):
        """
        Handles the user authorization process and returns an authorization
        URL.

        Returns:
            str: The authorization URL.
        """
        try:
            return self.twitch.get_auth_url()
        except Exception as request_error:
            self.twitch.logger.error("Failed to handle authorization: %s", str(request_error))
            raise

    def is_valid_notification(self, request):
        """
        Checks if a Twitch webhook notification is valid by comparing the
        provided signature to a computed one.

        Args:
            request: The incoming webhook request.

        Returns:
            bool: True if the notification is valid, False otherwise.
        """

        provided_signature = request.headers.get('Twitch-Eventsub-Message-Signature')
        computed_signature = self.compute_signature(request)

        return provided_signature == computed_signature

    def compute_signature(self, request) -> str:
        """
        Computes the HMAC SHA256 signature for a request.

        Args:
            request: The incoming webhook request.

        Returns:
            str: The computed HMAC SHA256 signature.
        """

        message_id = request.headers.get('Twitch-Eventsub-Message-Id')
        timestamp = request.headers.get('Twitch-Eventsub-Message-Timestamp')
        body = request.get_data(as_text=True)

        message = message_id + timestamp + body
        signature = hmac.new(bytes(self.twitch.credentials['secret'], 'utf-8'), 
                             msg=bytes(message, 'utf-8'), 
                             digestmod=hashlib.sha256).hexdigest()

        return 'sha256=' + signature
