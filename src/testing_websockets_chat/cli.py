# -*- coding: utf-8 -*-
"""
    testing_websockets_chat.cli
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Command Line Interface
"""
import os
from . import __version__, logger
from .server import app, socketio


def main() -> None:
    """
    Main CLI Handler
    """
    server_port = os.getenv('PORT', 5000)

    log_level = os.getenv('LOG_LEVEL', 'INFO')
    if log_level == 'DEBUG':
        debug_mode = True
    else:
        debug_mode = False

    logger.info(f"Starting testing-websockets-chat {__version__} on port {server_port}")
    logger.debug("Also enabling debug")
    socketio.run(
        app,
        host='0.0.0.0',
        debug=debug_mode)


if __name__ == "__main__":
    main()
