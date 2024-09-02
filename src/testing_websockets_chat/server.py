# -*- coding: utf-8 -*-
"""
    testing_websockets_chat.server
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Flask server component
"""
import os
import json
import re
import time
from threading import Lock
from flask import Flask, render_template, request, session, redirect
from flask_socketio import SocketIO, emit, join_room, leave_room, rooms, disconnect
from . import logger

url_prefix = ''
app = Flask(__name__,
            static_url_path=f"{url_prefix}/static",
            root_path=os.getenv('ROOT_PATH', ''))
app.config['SECRET_KEY'] = 'senhasecreta'
app.secret_key = app.config['SECRET_KEY']

socketio = SocketIO(app)

# background jobs
thread_user_list = None
thread_user_list_lock = Lock()
thread_housekeeping = None
thread_housekeeping_lock = Lock()

# stats
users = {
    'SERVER': {
        'sid': 'unused',
        'last_comm': 'unused',
        'channels': []
    }
}

channels = {
    '#general': {
        'topic': 'General chatting',
        'users': []
    }
}

sessions = {
    'SERVER_SID': 'SERVER'
}

protected_nicknames = ['SERVER', 'ALL']
protected_channels = ['#SERVER']


@app.route(f"{url_prefix}/")
def index():
    try:
        message = request.args['message']
    except KeyError:
        message = None

    try:
        if not session['nick']:
            logger.debug("Session nick is not set. Redirecting to login.")
            return render_template('login.html',
                                   message=message)
        else:
            logger.debug("Session nick is already set. Redirecting to chat.")
            return render_template('chat.html',
                                   nick=session['nick'])
    except KeyError:
        logger.debug("Session data key nick does not exist.")
        return render_template('login.html',
                               message=message)


@app.route(f"{url_prefix}/login", methods=['POST'])
def login():
    global users

    try:
        nick = request.form['nick']
        message = check_if_valid_nick(nick)

        if type(message) is bool:
            session['nick'] = nick
        elif type(message) is str:
            return redirect(f"/?message={message}", code=302)

    except KeyError:
        pass

    return redirect('/', code=302)


@app.route(f"{url_prefix}/logout")
def logout():
    try:
        if session['nick']:
            session['nick'] = None

    except KeyError:
        pass

    return redirect("/", code=302)


@socketio.on('connect')
def handle_connect():
    logger.debug(f"Websocket client connected ({request.sid})")

    # disconnect user if he's already connected on another websocket
    try:
        if sessions[request.sid] != session['nick']:
            logger.debug(f"Disconnecting websocket with duplicated user: ({session['nick']})")
            disconnect()
    except KeyError:
        pass

    # periodically send user list to all users
    global thread_user_list
    with thread_user_list_lock:
        if thread_user_list is None:
            thread_user_list = socketio.start_background_task(bg_send_user_list, socketio, 60)

    # periodically do the housekeeping
    # global thread_housekeeping
    # with thread_housekeeping_lock:
    #     if thread_housekeeping is None:
    #         thread_housekeeping = socketio.start_background_task(bg_housekeeping, socketio, 10)


@socketio.on('disconnect')
def handle_disconnect():
    logger.debug(f"Websocket client disconnected ({request.sid})")

    if session['nick']:
        remove_user(socketio, session['nick'], request.sid)


@socketio.on('message')
def handle_message(data: str) -> bool:
    logger.debug(f"Message received: {data}")

    try:
        json_data = json.loads(data)
    except json.decoder.JSONDecodeError:
        logger.debug(f"Could not decode JSON: {data}")
        send_error('Could not decode JSON.', socketio, request.sid)
        return False

    try:
        msg = {
            "nick": str(json_data['nick']),
            "channel": str(json_data['channel']),
            "message": str(json_data['message']),
            "timestamp": int(time.time())
        }
    except KeyError:
        logger.debug(f"Unknown fields on JSON: {data}")
        send_error('Unknown fields on JSON. Check what you sent.', socketio, request.sid)
        return False

    # check if the nick is from the user
    if not request.sid == users[msg['nick']]['sid']:
        logger.debug(f"Message contains an impersonator: {data}")
        send_error('You\'re not supposed to be you! Send another nick.', socketio, request.sid)
        return False

    # check if message has between 1 and 300 characters
    msg_len = len(msg['message'])
    if msg_len < 1 or msg_len > 300:
        logger.debug('Message has less than 1 or more than 300 characters. Discarding.')
        send_error('Message has less than 1 or more than 300 characters. Discarding.', socketio, request.sid)
        return False

    logger.debug(f"Broadcasting message: {data}")
    emit('response', json.dumps(msg), to=msg['channel'])
    return True


@socketio.on('server_message')
def handle_server_messages(data):
    global users, channels
    logger.debug(f"Server message received: {data}")

    try:
        json_data = json.loads(data)
    except json.decoder.JSONDecodeError:
        logger.debug(f"Could not decode JSON: {data}")
        send_error('Could not decode JSON.', socketio, request.sid)
        return False

    # user entered chat
    if re.match(r'^CONN ', json_data['message']):
        nick = re.sub(r'^CONN ', '', json_data['message'])

        message = check_if_valid_nick(nick)
        if type(message) is str:
            session['nick'] = None
            return redirect(f"/?message={message}", code=302)

        logger.debug(f"Detected new user entering the chat: {nick}")
        users[nick] = {
            'sid': request.sid,
            'channels': []
        }
        sessions[request.sid] = nick

        # joins the default general channel
        join_room('#general')
        channels['#general']['users'].append(nick)
        users[nick]['channels'].append('#general')

        msg = {
            "nick": "SERVER",
            "channel": "#general",
            "message": f"{nick} joined #general channel.",
            "timestamp": int(time.time())
        }
        socketio.emit('response', json.dumps(msg), to='#general')

        logger.debug(f"{nick} joined #general channel.")
        send_user_list(socketio, '#general')
        send_user_list(socketio)
        send_user_joined_channels(socketio, nick)
        return True

    elif re.search(r'^TEST$', json_data['message']):
        logger.debug("to aqui")
        user_ping()
        return True

    elif re.search(r'^STATS$', json_data['message']):
        logger.debug('Returning server statistics')
        message = f"Sessions ({len(sessions)-1}):\n\n"

        for sid in [k for k in sessions if sessions[k] != 'SERVER']:
            message = f"{message}{sid}: {sessions[sid]}\n"

        message = f"{message}\nUsers ({len(users)-1}):\n\n"

        for user in [k for k in users if k != 'SERVER']:
            message = f"{message}{user}"

        send_server_msg(socketio, message, session['nick'])
        return True

    elif re.search(r'^WHO$', json_data['message']):
        logger.debug('Returning everyone on the server')

        message = 'Nick: Session ID'
        for key in users:
            message = f"{message}\n{key}: {users[key]['sid']}"

        send_server_msg(socketio, message, session['nick'])
        return True

    elif re.search(r'^LIST$', json_data['message']):
        logger.debug(f"Returning channel list to {session['nick']}")

        message = 'Available channels:'
        count = 0
        max = 50
        for key in channels:
            count = count + 1
            message = f"{message}\n{key}"
            if count >= max:
                message = f"{message}\n...and more..."
                break

        send_server_msg(socketio, message, session['nick'])
        return True

    elif re.match(r'^NICK ', json_data['message']):
        old_nick = session['nick']
        new_nick = re.sub(r'^NICK ', '', json_data['message'])
        logger.debug(f"Changing {old_nick} nickname to {new_nick}")

        message = check_if_valid_nick(new_nick)
        if type(message) is str:
            send_server_msg(socketio, message, old_nick)
            return False

        session['nick'] = new_nick

        # change nick on the user list
        users[new_nick] = users[old_nick]
        remove_user(socketio, old_nick, request.sid, quiet=True)

        # change nick on the channel list
        for channel in users[new_nick]['channels']:
            channels[channel]['users'].append(new_nick)
            send_user_list(socketio, channel)

        send_user_list(socketio)

        msg = {
            "command": "CHANGE_NICK",
            "value": new_nick,
            "timestamp": int(time.time())
        }
        emit('server_command', json.dumps(msg), to=request.sid)

        message = f"Your nick is now {new_nick}"
        send_server_msg(socketio, message, new_nick)
        return True

    elif re.search(r'^JOIN ', json_data['message']):
        channel_name = re.sub(r'^JOIN #?', '', json_data['message'])
        channel_name = f"#{channel_name}"
        channel_name = channel_name.lower()

        message = check_if_valid_channel(channel_name)
        if type(message) is str:
            send_server_msg(socketio, message, session['nick'])
            return False

        msg = {
            "command": "CHANGE_CHANNEL",
            "value": channel_name,
            "timestamp": int(time.time())
        }
        emit('server_command', json.dumps(msg), to=request.sid)

        if channel_name not in rooms():
            logger.debug(f"User {json_data['nick']} joining channel {channel_name}")

            if not channels.get(channel_name):
                channels[channel_name] = {
                    'topic': channel_name,
                    'users': []
                }

            join_room(channel_name)

            msg = {
                "nick": "SERVER",
                "channel": channel_name,
                "message": f"{json_data['nick']} joined {channel_name} channel.",
                "timestamp": int(time.time())
            }
            emit('response', json.dumps(msg), to=channel_name)

            channels[channel_name]['users'].append(json_data['nick'])
            users[json_data['nick']]['channels'].append(channel_name)

        send_user_list(socketio, channel_name)
        send_user_joined_channels(socketio, json_data['nick'])
        return True

    elif re.search(r'^(PART|LEAVE)$', json_data['message']):
        json_data['channel'] = json_data['channel'].lower()

        # don't let the user leave #general
        if json_data['channel'] == '#general':
            return False

        logger.debug(f"User {json_data['nick']} leaving channel {json_data['channel']}")

        msg = {
            "nick": "SERVER",
            "channel": json_data['channel'],
            "message": f"{json_data['nick']} has left the {json_data['channel']} channel.",
            "timestamp": int(time.time())
        }
        emit('response', json.dumps(msg), to=json_data['channel'])
        leave_room(json_data['channel'])

        try:
            channels[json_data['channel']]['users'].remove(json_data['nick'])
            users[json_data['nick']]['channels'].remove(json_data['channel'])
            send_user_list(socketio, json_data['channel'])
        except ValueError:
            pass

        msg = {
            "command": "CHANGE_CHANNEL",
            "value": '#general',
            "timestamp": int(time.time())
        }
        emit('server_command', json.dumps(msg), to=users[json_data['nick']]['sid'])
        send_user_joined_channels(socketio, json_data['nick'])
        return True


@socketio.on('pong')
def handle_pong(data: str) -> None:
    """
    Receives a ping reply from the server and writes the last communication time
    to the user list

    Args:
        data (str): Data from the ping reply. It's not used as of now.
    """
    pass


def remove_user(socketio: SocketIO, nick: str, sid: str = None, quiet: bool = False) -> bool:
    """
    Removes the user from our counters/structures

    Args:
        nick (str): Nickname of the user
        sid (str|Optional): Session ID of the websocket
        quiet (bool|Optional): If true, it doesn't send any messages about removing the user

    Returns:
        bool: True if user was removed. False otherwise.
    """
    global users

    if not sid:
        try:
            sid = users[nick]['sid']
        except KeyError:
            logger.debug(f"Couldnt remove user {nick}, sid not found")
            return False

    try:
        # check if user is consistent in both data structures
        if users[nick]['sid'] == sid and sessions[sid] == nick:
            logger.debug(f"Removing user from server: {nick}")

            # remove user from each channel he belongs
            for channel in users[nick]['channels']:
                try:
                    channels[channel]['users'].remove(nick)
                    if not quiet:
                        msg = {
                            "nick": "SERVER",
                            "channel": channel,
                            "message": f"{nick} has left the {channel} channel.",
                            "timestamp": int(time.time())
                        }
                        socketio.emit('response', json.dumps(msg), to=channel)
                        send_user_list(socketio, channel)
                except ValueError:
                    pass

            # remove user from user list
            try:
                users.pop(nick)
            except ValueError:
                pass

            # remove the nick from session id
            sessions.pop(sid)

            send_user_list(socketio)
            return True

    except KeyError:
        return False


def check_if_valid_nick(nick: str) -> [bool, str]:
    """
    Check if nickname can be used.

    Args:
        nick (str): nickname to check

    Returns:
        bool|str: True if it can be used, a string containing the error if it cannot.
    """
    global users, protected_nicknames

    lowercase_users = [k.lower() for k in users.keys()]
    if not re.search(r'^[\w-]{1,50}?$', nick):
        return 'Nick should use only unicode characters, with length of 1 to 50.'

    elif str(nick).lower() in lowercase_users:
        return 'Nick is already online at the moment.'

    if nick in protected_nicknames:
        return 'Nick is protected.'

    return True


def check_if_valid_channel(channel: str) -> [bool, str]:
    """
    Check if channel name can be used.

    Args:
        channel (str): channel to check

    Returns:
        bool|str: True if it can be used, a string containing the error if it cannot.
    """
    global protected_channels

    if not re.search(r'^#?[A-Za-z0-9_-]{1,50}?$', channel):
        return 'Channel should use only alphanumeric characters, _ and -, with length of 1 to 50.'

    elif channel in protected_channels:
        return 'Channel is protected'

    return True


def send_error(message: str, socketio: SocketIO, sid: str) -> None:
    msg = {
        "nick": "SERVER",
        "message": message,
        "timestamp": int(time.time())
    }

    socketio.emit('client_error', json.dumps(msg), to=sid)


def send_user_list(socketio: SocketIO, channel: str = "all") -> None:
    global users, channels

    if channel == "all":
        msg = {
            "command": "GLOBAL_USER_LIST",
            "value": [k for k in users.keys() if k != 'SERVER'],
            "timestamp": int(time.time())
        }

        logger.debug("Sending global user list to all users.")
        socketio.emit('server_command', json.dumps(msg))

    else:
        msg = {
            "command": "CHANNEL_USER_LIST",
            "value": {
                "channel": channel,
                "users": channels[channel]['users']
            },
            "timestamp": int(time.time())
        }

        logger.debug(f"Sending channel user list to channel {channel}.")
        emit('server_command', json.dumps(msg), to=channel)


def send_user_joined_channels(socketio: SocketIO, nick: str) -> None:
    global users

    channels = users[nick]['channels']
    sid = users[nick]['sid']

    msg = {
        "command": "USER_JOINED_CHANNELS",
        "value": channels,
        "timestamp": int(time.time())
    }

    logger.debug(f"Sending user joined channels to {nick}.")
    socketio.emit('server_command', json.dumps(msg), to=sid)


def send_server_msg(socketio: SocketIO, message: str, nick: str) -> bool:
    try:
        sid = users[nick]['sid']
    except KeyError:
        return False

    msg = {
        "nick": "SERVER",
        "channel": "current",
        "message": message,
        "timestamp": int(time.time())
    }
    emit('response', json.dumps(msg), to=sid)
    return True


def user_ping() -> None:
    """
    Sends a ping to all users
    """
    emit('ping', '{}', broadcast=True, include_self=False)


def housekeeping(socketio: SocketIO) -> None:
    """
    Tries to clean up the server as much as possible. For example, cleaning
    up unused rooms and stale users.

    Args:
        socketio: the socketio server to do the cleanup.
    """
    global users, channels

    logger.debug('Housekeeping: closing unused rooms')
    remove_channels = []
    for channel in channels:
        if channel == '#general':
            continue

        if len(channels[channel]['users']) == 0:
            socketio.close_room(channel)
            remove_channels.append(channel)

    if len(remove_channels) > 0:
        logger.debug(f"Housekeeping: removing rooms from list - {'-'.join(remove_channels)}")
        for channel in remove_channels:
            channels.pop(channel)


def bg_send_user_list(socketio: SocketIO, sleep: int = 0) -> None:
    while True:
        socketio.sleep(sleep)
        send_user_list(socketio)


def bg_housekeeping(socketio: SocketIO, sleep: int = 0) -> None:
    while True:
        socketio.sleep(sleep)
        housekeeping(socketio)
