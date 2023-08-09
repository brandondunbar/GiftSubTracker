"""
constants.py

This module loads and sets up the constants for the project. It uses the
load_envs module to load and validate the required environment variables.

After loading and validating the environment variables, it assigns them to
the corresponding constants. It also defines some additional constants that
are used in the project.
"""

from load_envs import load_environment_variables

# Load and validate environment variables
env_vars = load_environment_variables()

# Assign environment variables to constants
GCP_PROJECT_ID = env_vars['GCP_PROJECT_ID']
GOOGLE_APPLICATION_CREDENTIALS = env_vars['GCP_KEY_PATH']
TWITCH_CLIENT_ID = env_vars['TWITCH_CLIENT_ID']
TWITCH_CLIENT_SECRET = env_vars['TWITCH_CLIENT_SECRET']
TWITCH_HUB_SECRET = env_vars['TWITCH_HUB_SECRET']
FLASK_SECRET = env_vars['FLASK_SIGNING_SECRET']

# Define other constants
DOMAIN_NAME = "https://9269-50-26-233-27.ngrok-free.app"
PORT = 8080
REF_SPREADSHEET_ID = "17v8nY-CNssb6VRA2WQhDT6mmfhB4cWqCBZuZj1KDjuI"

# General constants
UNICODE_A_VALUE = 65
