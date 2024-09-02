# -*- coding: utf-8 -*-
"""
    testing_websockets_chat
    ~~~~~~~~~~~~~~~~~~~~~~~

    Just testing a websockets chat
"""
import logging
import os

__author__ = 'Eitch'
__version__ = '1.0.0'

logging.basicConfig(
    format='[%(asctime)s] [%(levelname)s] %(message)s'
)
logging.getLogger().setLevel(os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("testing_websockets_chat")
