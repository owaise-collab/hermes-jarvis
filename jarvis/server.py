"""Loopback-only Jarvis panel. No external assets, arbitrary commands or cloud routes."""
from __future__ import annotations
import argparse
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import os
from pathlib import Path
import secrets
import subprocess
import threading
from urllib.parse import parse_qs, urlsplit
import wave

from core import Jobs, LocalModel, Vault, printable

STATIC = Path(__file__).parent / 'static'


class Speech:
    def __init__(self, home):
        self.home = Path(home)
        self.lock = threading.Lock()
        self.whisper = None
        self.piper = None

    def status(self):
        import importlib.util
        voice = self.home / 'cache' / 'piper-voices' / 'en_US-lessac-medium.onnx'
        return {'tts': bool(importlib.util.find_spec('piper')) and voice.is_file(),
                'stt': bool(importlib.util.find_spec('faster_whisper')),
                'note': 'Speech requires installed local models. Missing Whisper cache fails without downloading.'}

    def transcribe(self, data):
        import numpy as np
        from faster_whisper import WhisperModel
        with wave.open(io.BytesIO(data), 'rb') as audio:
            if (audio.getnchannels() != 1 or audio.getsampwidth() != 2 or
                    audio.getframerate() != 16000 or audio.getnframes() > 16000 * 60):
                raise ValueError('Use mono 16kHz PCM16 WAV, at most 60 seconds.')
            samples = np.frombuffer(audio.readframes(audio.getnframes()), dtype=np.int16).astype(np.float32) / 32768
        with self.lock:
            if self.whisper is None:
                self.whisper = WhisperModel('base', device='cpu', compute_type='int8', local_files_only=True)
            segments, info = self.whisper.transcribe(samples, language='en', vad_filter=True)
            return ' '.join(segment.text.strip() for segment in segments)

    def synthesize(self, text):
        from piper import PiperVoice
        voice = self.home / 'cache' / 'piper-voices' / 'en_US-lessac-medium.onnx'
        if not voice.is_file():
            raise ValueError('Local Piper voice is missing. Follow the voice installation guide.')
        with self.lock:
            if self.piper is None:
                self.piper = PiperVoice.load(str(voice), use_cuda=False)
            stream = io.BytesIO()
            with wave.open(stream, 'wb') as audio:
                self.piper.synthesize_wav(text, audio)
            return stream.getvalue()


class Handler(BaseHTTPRequestHandler):
    def __init__(self, *args, app, **kwargs):
        self.app = app
        super().__init__(*args, **kwargs)

    def log_message(self, fmt, *args):
        # Keep prompts, note names, tokens and transcripts out of HTTP logs.
        pass

    def send(self, status, data, content_type='application/json'):
        if content_type == 'application/json':
            data = json.dumps(data, ensure_ascii=False).encode('utf-8')
        elif isinstance(data, str):
            data = data.encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('X-Frame-Options', 'DENY')
        policy = "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; media-src 'self' blob:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        if content_type.startswith('text/html') and self.path.startswith('/print?'):
            policy = "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
        self.send_header('Content-Security-Policy', policy)
        self.send_header('Permissions-Policy', 'microphone=(self), camera=(), geolocation=()')
        self.end_headers()
        self.wfile.write(data)

    def valid_host(self):
        return self.headers.get('Host') == f'127.0.0.1:{self.server.server_port}'

    def authorized(self):
        token = self.headers.get('X-Jarvis-Token', '')
        return secrets.compare_digest(token, self.app['token'])

    def do_GET(self):
        if not self.valid_host():
            return self.send(403, {'error': 'Use the loopback URL printed by the launcher.'})
        route = urlsplit(self.path)
        query = parse_qs(route.query)
        try:
            if route.path in ('/', '/app.js', '/style.css'):
                name = {'/': 'index.html', '/app.js': 'app.js', '/style.css': 'style.css'}[route.path]
                content = (STATIC / name).read_text(encoding='utf-8')
                if name == 'index.html':
                    content = content.replace('__TOKEN__', self.app['token'])
                kind = {'html': 'text/html; charset=utf-8', 'js': 'application/javascript', 'css': 'text/css'}[name.rsplit('.', 1)[1]]
                return self.send(200, content, kind)
            if not self.authorized():
                return self.send(403, {'error': 'Refresh the local panel to reconnect.'})
            if route.path == '/api/status':
                return self.send(200, {'model': self.app['model'].health(),
                    'speech': self.app['speech'].status(), 'vault': str(self.app['vault'].root),
                    'active_job': self.app['jobs'].active, 'mode': 'local-only',
                    'workflows': ['chat', 'lesson', 'carousel', 'video', 'worksheet']})
            if route.path == '/api/notes':
                return self.send(200, self.app['vault'].list(query.get('q', [''])[0][:200]))
            if route.path == '/api/note':
                return self.send(200, {'content': self.app['vault'].read(query['path'][0])})
            if route.path == '/api/brief':
                return self.send(200, {'content': self.app['vault'].brief()})
            if route.path.startswith('/api/jobs/'):
                return self.send(200, self.app['jobs'].get(route.path.rsplit('/', 1)[1]))
            return self.send(404, {'error': 'Not found.'})
        except (OSError, ValueError, KeyError) as exc:
            return self.send(400, {'error': str(exc)})

    def do_POST(self):
        origin = self.headers.get('Origin')
        expected = f'http://127.0.0.1:{self.server.server_port}'
        if not self.valid_host() or not self.authorized() or (origin is not None and origin != expected):
            return self.send(403, {'error': 'Request must originate from this local panel.'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 2_000_000:
                return self.send(413, {'error': 'Request too large or empty.'})
            data = self.rfile.read(length)
            if self.path == '/api/transcribe':
                return self.send(200, {'text': self.app['speech'].transcribe(data)})
            if not self.headers.get('Content-Type', '').startswith('application/json'):
                return self.send(415, {'error': 'Expected JSON.'})
            body = json.loads(data)
            if not isinstance(body, dict):
                raise ValueError('Expected a JSON object.')
            if self.path == '/api/notes':
                name = self.app['vault'].save(body.get('area', 'raw'), body.get('title'), body.get('content'))
                return self.send(201, {'path': name})
            if self.path == '/api/jobs':
                job = self.app['jobs'].submit(body.get('kind'), body.get('prompt'), body.get('notes', []))
                return self.send(202, job)
            if self.path == '/api/hermes':
                launcher = self.app['speech'].home / 'Start-HermesDesktopLocal.ps1'
                if os.name != 'nt' or not launcher.is_file():
                    raise ValueError('Native Desktop launcher not found. Open Hermes Desktop from your existing shortcut.')
                subprocess.Popen(['powershell.exe', '-NoProfile', '-File', str(launcher)],
                    cwd=str(launcher.parent), creationflags=subprocess.CREATE_NO_WINDOW,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return self.send(202, {'message': 'Requested Hermes Desktop. It runs separately from this panel.'})
            if self.path == '/api/shutdown':
                if self.app['jobs'].active:
                    raise ValueError('Wait for the active model job before stopping the panel.')
                self.send(200, {'message': 'Jarvis panel stopped. Vault files and the model server are preserved.'})
                threading.Thread(target=self.server.shutdown, daemon=True).start()
                return
            if self.path == '/api/speak':
                text = body.get('text', '')
                if not isinstance(text, str) or not 0 < len(text) <= 3000:
                    raise ValueError('Speech text must contain 1–3,000 characters.')
                return self.send(200, self.app['speech'].synthesize(text), 'audio/wav')
            if self.path == '/api/print':
                text = body.get('text', '')
                if not isinstance(text, str) or len(text) > 150_000:
                    raise ValueError('Invalid print content.')
                # Return escaped print document for a local Blob preview.
                return self.send(200, {'html': printable(text)})
            return self.send(404, {'error': 'Not found.'})
        except (ValueError, KeyError, TypeError, OSError, ImportError, RuntimeError, wave.Error) as exc:
            return self.send(400, {'error': str(exc)})


def create_server(home, data, port=9120, endpoint='http://127.0.0.1:8080/v1', model='local-hermes'):
    vault, llm = Vault(Path(data) / 'vault'), LocalModel(endpoint, model)
    app = {'vault': vault, 'model': llm, 'jobs': Jobs(vault, llm),
           'speech': Speech(home), 'token': secrets.token_urlsafe(32)}
    return ThreadingHTTPServer(('127.0.0.1', port), partial(Handler, app=app))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hermes-home', required=True, type=Path)
    parser.add_argument('--data-dir', type=Path)
    parser.add_argument('--port', type=int, default=9120)
    parser.add_argument('--endpoint', default='http://127.0.0.1:8080/v1')
    parser.add_argument('--model', default='local-hermes')
    parser.add_argument('--open-browser', action='store_true')
    args = parser.parse_args()
    # These libraries must use their existing caches, even if a download helper is invoked.
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    server = create_server(args.hermes_home, args.data_dir or args.hermes_home / 'jarvis-data',
                           args.port, args.endpoint, args.model)
    print(f'Jarvis: http://127.0.0.1:{server.server_port} — Ctrl+C to stop.', flush=True)
    if args.open_browser:
        import webbrowser
        webbrowser.open(f'http://127.0.0.1:{server.server_port}')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
