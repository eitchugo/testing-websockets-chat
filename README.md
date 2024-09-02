# Testing websockets chat

An example web application that supports websockets to create chat rooms.

This is just for fun and there's no storage for anything. Each run resets everything.

- Uses [Flask](https://flask-docs.readthedocs.io/en/latest/) for webserver
- [Flask-SocketIO](https://flask-socketio.readthedocs.io/en/latest/) for enabling a Socket.IO server inside flask
- [FG Emoji Picker](https://github.com/woody180/vanilla-javascript-emoji-picker) for the emoji widget
- Vanilla javascript

https://github.com/user-attachments/assets/89ceccd3-4ff7-4fc2-a75c-5a9cf9da9297

## Using

```bash
python -m venv venv
source venv/bin/activate
pip install -e .
LOG_LEVEL=DEBUG testing-websockets-chat-server
```

Access the application on http://127.0.0.1:5000 within a browser and have fun.

## TODO

- Image uploads
- Documentation about protocol
