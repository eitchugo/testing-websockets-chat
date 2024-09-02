# -*- coding: utf-8 -*-
"""
    testing-websockets-chat
    ~~~~~~~~~~~~~~~~~~~~~~~

    Setup script for packaging and installing testing-websockets-chat
"""
import pathlib
from setuptools import setup, find_packages

this_directory = pathlib.Path(__file__).parent.resolve()
long_description = (this_directory / 'README.md').read_text(encoding='utf-8')

setup(
    name="testing-websockets-chat",
    version="1.0.0",
    description=("Testing websockets chat"),
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Hugo Cisneiros (Eitch)',
    author_email='eitch@naovouler.com.br',
    classifiers=[
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3 :: Only',
    ],
    keywords='testing',
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.11, <4",
    install_requires=[
        "flask==3.0.3",
        "Flask-SocketIO==5.3.6",
        "eventlet==0.36.1"
    ],
    entry_points={
        'console_scripts': [
            'testing-websockets-chat-server=testing_websockets_chat.cli:main',
        ],
    },
)
