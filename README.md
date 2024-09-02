# Testing websockets chat

An example web application that supports websockets to create chat rooms.

This is just for fun and there's no storage for anything. Each run resets everything.

https://raw.githubusercontent.com/eitchugo/testing-websockets-chat/main/demo.mp4

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
