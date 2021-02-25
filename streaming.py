import sys
import os
import mimetypes
from flask import Flask, request, Response, send_from_directory, send_file, make_response, url_for, render_template
import socket
import subprocess
import re
import ffmpeg
import jinja2

TYPES = {
    "Flask": "/stream_video_flask",
    "FFMPEG": "/stream_video_ffmpeg",
    "Chunks": "/stream_video_chunks"
}
URL = TYPES['Flask']

PORT = 5000
HOST = socket.gethostbyname(socket.gethostname())

filename = sys.argv[1]
file_dir = os.path.dirname(filename)
file_path = file_dir + filename
mimetype = mimetypes.MimeTypes().guess_type(file_path)[0]
file_size = os.stat(file_path).st_size

FFMPEG_VIDEO = f'ffmpeg -i \"{file_path}\" -movflags frag_keyframe+empty_moov -f webm -'

HTML = """
<!doctype html>
<html>
    <body>
        <div id='container' style='width:100%; height:100%;'>
            <video id="video" src="$URL"
                width="1280" height="720" poster=""
                preload="auto" controls loop>
            </video>
            <div id='status'></div>
        </div>
        <script src='/static/subtitles-octopus.js'></script>
        <script>
            var video = document.getElementById('video');
            var div = document.getElementById('status');
            var options = {
                video: video,
                subUrl: '/sub', // Link to subtitles
                workerUrl: '/static/subtitles-octopus-worker.js', // Link to WebAssembly-based file "libassjs-worker.js"
                legacyWorkerUrl: '/static/subtitles-octopus-worker-legacy.js' // Link to non-WebAssembly worker
            };
            var ass = new SubtitlesOctopus(options);
        </script>
    </body>
</html>
""".replace("$URL", "/static/videos/yuru.mp4")


HTML_VIDEOJS = """
<head>
  <link href="https://vjs.zencdn.net/7.10.2/video-js.css" rel="stylesheet" />
</head>
<body>
  <video
    id="my-video"
    class="video-js"
    controls
    preload="auto"
    width="640"
    height="264"
    data-setup='{}'
  >
    <source src="$URL" type="video/mp4" />
    <p class="vjs-no-js">
      To view this video please enable JavaScript, and consider upgrading to a
      web browser that
      <a href="https://videojs.com/html5-video-support/" target="_blank"
        >supports HTML5 video</a
      >
    </p>
  </video>

  <script src="https://vjs.zencdn.net/7.10.2/video.min.js"></script>
</body>
""".replace("$URL", URL)

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir))

app = Flask(__name__)


@app.after_request
def after_request_func(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    if '.wasm' in request.url:
        response.headers['Content-Type'] = 'application/wasm'
    return response


@app.route('/')
def index():
    return HTML

@app.route('/stream_video_flask')
def stream_video_flask():
    return send_from_directory(file_dir, filename, conditional=True)


@app.route('/stream_video_ffmpeg')
def stream_video_ffmpeg():
    video_proc = subprocess.Popen(
        FFMPEG_VIDEO, shell=True, stdout=subprocess.PIPE)

    def gen():
        for data in iter(video_proc.stdout.readline, b''):
            yield data
        # proc_video.kill()
        # outs, errs = proc_video.communicate()
    return Response(gen(), mimetype=mimetype)


@app.route('/stream_video_chunks')
def stream_video_chunks():
    def get_range():
        range_header = request.headers.get('Range', None)

        if not range_header:
            return
        start, end = 0, None
        match = re.search(r'(\d+)-(\d*)', range_header)
        groups = match.groups()

        if groups[0]:
            start = int(groups[0])
        if groups[1]:
            end = int(groups[1])

        return start, end

    def get_chunk(start, end):
        length = 1 << 20

        if end:
            length = end + 1 - start
        else:
            length = file_size - start

        with open(file_path, 'rb') as f:
            f.seek(start)
            chunk = f.read(length)

        return chunk, length

    start, end = get_range()
    chunk, length = get_chunk(start, end)
    resp = Response(chunk, 206, mimetype=mimetype,
                    content_type=mimetype, direct_passthrough=True)

    resp.headers.add('Accept-Ranges', 'bytes')
    resp.headers.add(
        'Content-Range', f'bytes {start}-{start + length - 1}/{file_size}')

    return resp


@app.route('/sub')
def ass():
    file_path = './yuru265.mkv'
    try:
        return (ffmpeg
                    .input(file_path)
                    .output('-', f='ass', map='0:s:m:language:por?')
                    .global_args('-hide_banner', '-loglevel', 'error')
                    .run(capture_stdout=True)
        )
    except:
        return ''

def startFlask():
    print(f'Access http://{HOST}:{PORT}/ from any device in local network')
    app.run(host='0.0.0.0', port=PORT, threaded=True)


if __name__ == "__main__":
    if not len(sys.argv) == 2:
        print('Usage: python streaming.py path/to/video')
    else:
        startFlask()
