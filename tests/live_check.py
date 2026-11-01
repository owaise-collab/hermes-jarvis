"""Explicit live loopback + synthetic speech smoke test. Saves its report outside the repo."""
import argparse
import io
import json
import os
from pathlib import Path
import re
import sys
import time
import urllib.request
import wave

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'jarvis'))
from server import Speech


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hermes-home', type=Path, required=True)
    parser.add_argument('--port', type=int, default=9120)
    args = parser.parse_args()
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    base = f'http://127.0.0.1:{args.port}'
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    page = opener.open(base, timeout=5).read().decode()
    token = re.search(r'name="jarvis-token" content="([^"]+)"', page)[1]
    def api(path, body=None):
        request = urllib.request.Request(base + path, data=json.dumps(body).encode() if body is not None else None,
            headers={'X-Jarvis-Token': token, 'Content-Type': 'application/json'})
        return json.load(opener.open(request, timeout=15))
    report = {'scope': 'Actual loopback panel/model and synthetic local speech; no microphone capture or speaker playback', 'checks': {}}
    report['status'] = api('/api/status')
    report['checks']['model_ready'] = report['status']['model']['ready']
    report['checks']['brief'] = 'Local vault brief' in api('/api/brief')['content']
    job = api('/api/jobs', {'kind': 'chat', 'prompt': 'Reply with exactly JARVIS_LOCAL_OK.', 'notes': []})
    deadline = time.monotonic() + 650
    while time.monotonic() < deadline:
        state = api('/api/jobs/' + job['id'])
        if state['status'] != 'running':
            break
        time.sleep(2)
    report['checks']['local_model_job'] = state['status'] == 'completed' and 'JARVIS_LOCAL_OK' in state['answer']
    report['model_response'] = state
    speech = Speech(args.hermes_home)
    sample = speech.synthesize('My local voice is ready to help with tasks.')
    with wave.open(io.BytesIO(sample), 'rb') as audio:
        report['checks']['piper_audio'] = audio.getnframes() > 0
        import numpy as np
        samples = np.frombuffer(audio.readframes(audio.getnframes()), dtype=np.int16).astype(np.float32)
        # Resample this synthetic test to the exact browser-upload contract.
        count = int(len(samples) * 16000 / audio.getframerate())
        resampled = np.interp(np.linspace(0, len(samples)-1, count), np.arange(len(samples)), samples).astype(np.int16)
    converted = io.BytesIO()
    with wave.open(converted, 'wb') as audio:
        audio.setnchannels(1); audio.setsampwidth(2); audio.setframerate(16000)
        audio.writeframes(resampled.tobytes())
    transcript = speech.transcribe(converted.getvalue())
    report['synthetic_transcript'] = transcript
    report['checks']['whisper_roundtrip'] = all(word in transcript.lower() for word in ('local', 'voice', 'tasks'))
    out = args.hermes_home / 'runtime' / 'jarvis-verification.json'
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'checks': report['checks'], 'report': str(out)}, indent=2))
    if not all(report['checks'].values()):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
