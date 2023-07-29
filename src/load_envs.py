"""
load_envs.py

This module contains a function to load environment variables from a .env
file and validate their existence.
It is designed to be used by the constants.py module.
"""

import os
from dotenv import load_dotenv


def load_environment_variables():
    """
    Loads environment variables from a .env file. Raises an error if any
    required variable is not set.

    Returns:
        A dictionary mapping environment variable names to their values.
    """

    # Load environment variables from .env file
    load_dotenv()

    # Define required environment variable names
    required_vars = [
        'GCP_PROJECT_ID', 'GCP_KEY_PATH', 'TWITCH_CLIENT_ID',
        'TWITCH_CLIENT_SECRET', 'TWITCH_HUB_SECRET', 'FLASK_SIGNING_SECRET'
    ]

    # Load and validate required environment variables
    env_vars = {}
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            raise EnvironmentError(f"Missing environment variable: {var}")
        env_vars[var] = value

    return env_vars
