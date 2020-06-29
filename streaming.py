import sys
import os
import mimetypes
import io
from flask import Flask, jsonify, request, render_template, Response, send_file, stream_with_context, make_response, send_from_directory
import socket

app = Flask(__name__)

@app.route('/')
def index():
	file = './'+sys.argv[1]
	return f"<video width='960' height='540' controls><source src=\"/send\" type=\"{mimetypes.MimeTypes().guess_type(file)[0]}\">Your browser does not support the video tag.</video>"

@app.route('/send')
def send():
    return send_from_directory('./', sys.argv[1], conditional=True)

def startFlask():
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    os.environ['WERKZEUG_RUN_MAIN'] = 'true'
    port = int(os.environ.get("PORT", 5432))
    print('Access http://{0}:{1}/ from any device in local network'.format(socket.gethostbyname(socket.gethostname()), port))
    app.run(host='0.0.0.0', port=port, threaded=True)

if __name__ == "__main__":
    if not len(sys.argv) == 2:
        print('Usage: python streaming.py path/to/video')
    else:
        startFlask()