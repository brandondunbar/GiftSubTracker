"""
main.py

This module is the entry point for the Sub Tracker application. The application
is responsible for running a web hook that listens for Twitch subscriptions at
the '/webhook' endpoint. When a gift subscription is detected, the application
updates a Google Sheet to track each viewer's gifted subscription count.

The application utilizes Flask to handle web requests and Flask-SocketIO for
WebSocket communication.
The application also interfaces with Google Sheets to maintain persistent data
and with the Twitch API for subscribing to and receiving events.

The module initializes a Flask application and a SocketIO server, then defines
route handlers for several endpoints, including:

- '/': The home page of the website.
- '/webhook': The endpoint that handles incoming requests from Twitch (for
both GET and POST methods).
- '/authorize': The endpoint that redirects the user to the Twitch
authorization URL.
- '/giftedsubs': The endpoint that processes incoming webhooks.
- '/reward': The endpoint that increments the rewards for a user.

The application is run by executing this module. The Flask-SocketIO server is
started, and the application begins listening for requests on the specified
port.
"""

# Import required modules
import logging
from flask import Flask, request, render_template, Response, redirect, url_for, session, jsonify
from flask_socketio import SocketIO
import constants
from services import configure_services
from webhook_handler import WebhookHandler

# Initialize Flask app and SocketIO
app = Flask(__name__)
app.secret_key = constants.FLASK_SECRET
socketio = SocketIO(app)

sheet_mgr, twitch, twitch_handler = configure_services()
logger = logging.getLogger(__name__)


@app.route('/')
def home():
    """
    Route for the home page of the website. Checks if the access token is
    valid, retrieves all rows from the Google sheet, and renders the home page
    template.

    Returns:
        A Response object with the rendered home page template.
    """

    # Check if the access token exists and is valid
    authorized = 'access_token' in session and \
        twitch.set_user_access_token_if_valid(session['access_token'])

    # Retrieve all rows from the Google sheet
    gifters = None
    if authorized:
        gifters = sheet_mgr.get_streamer_rows(session.get('broadcaster_id'))

    # Render and return the home page template
    return render_template("index.html", authorized=authorized, gifters=gifters)


@app.route('/webhook', methods=['GET'])
def handle_verification():
    """
    Route for handling the verification of the Twitch webhook. If an error is
    received, a response is returned with the error message. If no
    authorization code is received, a response is returned indicating that the
    code is missing. Otherwise, the user access token is requested, the
    broadcaster ID is retrieved, and a subscription is made to the EventSub.

    Returns:
        A Response object with a redirect to the home page.
    """

    print('/webhook get called')
    # Extract the authorization code from the request arguments
    auth_code = request.args.get('code')

    # If an error is received, return a response with the error message
    if request.args.get('error'):
        error_msg = f"Error: {request.args.get('error')}:"\
             f" {request.args.get('error_description')}"
        return Response(error_msg)

    # If no authorization code is received, return a response indicating
    # that the code is missing
    if not auth_code:
        return Response('Missing "code" argument.')

    # Request the user access token, retrieve the broadcaster ID, and subscribe
    # to EventSub
    session['access_token'] = twitch_handler.handle_verification(auth_code)
    session['broadcaster_id'] = twitch.get_broadcaster_id()

    # Make the session persistent and store the access token in the session
    session.permanent = True

    # Redirect to the home page
    return redirect(url_for('home'))


@app.route('/webhook', methods=['POST'])
def handle_webhook():
    """
    Route for handling incoming requests to the Twitch webhook. If the request
    is a subscription verification, the challenge is returned. Otherwise, the
    Google sheet and SocketIO server are updated with the gifted subs
    information.

    Returns:
        A Response object with 'OK' if the request is handled successfully, or
        the challenge string if the request is a subscription verification.
    """
    print('/webhook post called')
    # Extract the request data
    data = request.json

    # Create a WebhookHandler and handle the webhook
    streamer_sheet = sheet_mgr.get_streamer_sheet(
        session.get('broadcaster_id'))
    handler = WebhookHandler(streamer_sheet, socketio)
    response = handler.handle_webhook(data)

    # If the response is 'OK', return a response with 'OK'
    if response == 'OK':
        return Response('OK')
    # Otherwise, return a response with the challenge
    return Response(response, mimetype='text/plain')


@app.route('/authorize')
def authorize():
    """
    Route for authorizing the Twitch application. Redirects the user to the
    Twitch authorization URL.

    Returns:
        A Response object with a redirect to the Twitch authorization URL.
    """

    # Get the Twitch authorization URL
    url = twitch_handler.handle_authorization()

    # Redirect to the Twitch authorization URL
    return redirect(url)


@app.route('/giftedsubs', methods=['POST'])
def respond():
    """
    Route for updating the Google sheet with the gifted subs information from
    a webhook.

    Returns:
        A Response object with the status of the operation.
    """

    # Extract the request data
    data = request.get_json()
    values_dict = {
        'user_id': data['data']['user_id'],
        'user_name': data['data']['user_name'],
        'gifted_subs': data['data']['gifted_subs'],
        'rewards_given': 0
    }

    # Update the Google sheet with the gifted subs information
    user_sheet = sheet_mgr.get_streamer_sheet(session.get('broadcaster_id'))
    user_sheet.append_or_update_row(values_dict)

    # Return a response with the status of the operation
    return jsonify({'success': True})


@app.route('/reward', methods=['POST'])
def increment_rewards():
    """
    Route for incrementing the rewards of a user.

    Returns:
        A Response object with the status of the operation and the new rewards
        data.
    """

    # Attempt to get the user row from the Google sheet
    streamer_sheet = sheet_mgr.get_streamer_sheet(
        session.get('broadcaster_id'))
    rewards_given = streamer_sheet.increment_rewards_given(
        session.get('broadcaster_id'))

    # Return a response with the status of the operation and the new rewards
    # data
    return jsonify(
        {'success': True,
         'new_data': {'rewards_given': rewards_given}})


# Run the Flask app with SocketIO on the specified port
if __name__ == '__main__':
    server_start_msg = f"Starting server on port {constants.PORT}."
    logger.info(server_start_msg)
    socketio.run(app, port=constants.PORT)
