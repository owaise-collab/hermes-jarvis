"""Behavior tests in temporary homes. No live model, microphone or cloud service."""
import http.client
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'jarvis'))
sys.path.insert(0, str(ROOT / 'scripts'))
from core import Jobs, LocalModel, Vault, printable
from server import create_server
from install import install, local_settings, restore


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.vault = Vault(Path(self.temp.name) / 'vault')

    def test_capture_search_and_context(self):
        name = self.vault.save('raw', 'Kindness source', 'A verified reference about helping. العربية')
        self.assertEqual(self.vault.list('helping reference')[0]['path'], name)
        self.assertIn('العربية', self.vault.read(name))
        self.assertIn(name, self.vault.context([name]))

    def test_path_escape_is_rejected(self):
        for name in ('../config.yaml', 'raw/../../secret.md', 'raw/nested/file.md', 'outputs/a.txt', 'C:\\secret.md'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.vault.read(name)

    def test_local_endpoints_only(self):
        for endpoint in ('https://example.com/v1', 'http://127.0.0.1.evil/v1', 'http://localhost/v1', 'http://127.0.0.1/v1?x=1', 'http://u:p@127.0.0.1/v1'):
            with self.subTest(endpoint=endpoint), self.assertRaises(ValueError):
                LocalModel(endpoint)

    def test_brief_does_not_need_inference(self):
        self.vault.save('wiki', 'One useful lesson', 'Lesson notes')
        self.assertIn('One useful lesson', self.vault.brief())
        self.assertIn('not a news or calendar', self.vault.brief())

    def test_print_escapes_html(self):
        output = printable('<img src="https://example.com/track"><script>bad()</script>')
        self.assertNotIn('<script>bad()', output)
        self.assertIn('&lt;img', output)

    def test_jobs_save_output_and_reject_concurrency(self):
        started, finish = threading.Event(), threading.Event()
        class Model:
            def generate(self, *args):
                started.set()
                finish.wait(3)
                return 'A local draft'
        jobs = Jobs(self.vault, Model())
        job = jobs.submit('lesson', 'Teach kindness', [])
        self.assertTrue(started.wait(2))
        with self.assertRaises(ValueError):
            jobs.submit('chat', 'Another task', [])
        finish.set()
        for _ in range(100):
            if jobs.get(job['id'])['status'] != 'running':
                break
            time.sleep(.01)
        done = jobs.get(job['id'])
        self.assertEqual(done['status'], 'completed')
        self.assertIn('DRAFT', self.vault.read(done['note']))

    def test_model_failure_is_not_reported_as_success(self):
        class Model:
            def generate(self, *args):
                raise RuntimeError('Endpoint unavailable')
        jobs = Jobs(self.vault, Model())
        job = jobs.submit('chat', 'Hello', [])
        for _ in range(100):
            if jobs.get(job['id'])['status'] != 'running':
                break
            time.sleep(.01)
        self.assertEqual(jobs.get(job['id'])['status'], 'failed')
        self.assertFalse(self.vault.list())

    def test_route_settings_preserve_unrelated_config(self):
        config = {'display': {'theme': 'dark'}, 'fallback_model': 'remote', 'auxiliary': {'compression': {'provider': 'openrouter', 'api_key': 'placeholder'}}}
        local_settings(config, 'http://127.0.0.1:8080/v1', 'local-hermes')
        self.assertEqual(config['display']['theme'], 'dark')
        self.assertEqual(config['auxiliary']['compression']['provider'], 'main')
        self.assertEqual(config['auxiliary']['compression']['api_key'], '')
        self.assertNotIn('fallback_model', config)
        self.assertFalse(config['auth']['adopt_external_logins'])

    @unittest.skipUnless(importlib.util.find_spec('ruamel'), 'Requires Hermes environment')
    def test_install_dry_run_idempotency_and_rollback(self):
        home = Path(self.temp.name) / 'home'
        install(home, 'http://127.0.0.1:8080/v1', 'local-hermes', True)
        self.assertFalse(home.exists())
        home.mkdir()
        original = '# retained comment\ndisplay:\n  theme: dark\n'
        (home / 'config.yaml').write_text(original, encoding='utf-8')
        first = install(home, 'http://127.0.0.1:8080/v1', 'local-hermes')
        second = install(home, 'http://127.0.0.1:8080/v1', 'local-hermes')
        self.assertEqual((home / 'SOUL.md').read_text().count('## Jarvis local workspace'), 1)
        notes = Vault(home / 'jarvis-data/vault')
        name = notes.save('raw', 'Keep this', 'User content')
        restore(second)
        restore(first)
        self.assertEqual((home / 'config.yaml').read_text(), original)
        self.assertTrue(notes.resolve(name).exists())

    @unittest.skipUnless(importlib.util.find_spec('ruamel'), 'Requires Hermes environment')
    def test_rollback_refuses_to_overwrite_later_edits(self):
        home = Path(self.temp.name) / 'home'
        backup = install(home, 'http://127.0.0.1:8080/v1', 'local-hermes')
        (home / 'SOUL.md').write_text('New user instructions', encoding='utf-8')
        with self.assertRaises(ValueError):
            restore(backup)
        self.assertEqual((home / 'SOUL.md').read_text(), 'New user instructions')


class HttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.server = create_server(cls.temp.name, cls.temp.name, 0)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.temp.cleanup()

    def request(self, method, path, body=None, headers=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        connection.request(method, path, body, headers or {})
        response = connection.getresponse()
        status, data = response.status, response.read()
        connection.close()
        return status, data

    def token(self):
        status, data = self.request('GET', '/')
        self.assertEqual(status, 200)
        import re
        return re.search(rb'name="jarvis-token" content="([^"]+)"', data)[1].decode()

    def test_api_requires_token(self):
        self.assertEqual(self.request('GET', '/api/notes')[0], 403)

    def test_dns_rebinding_host_rejected(self):
        self.assertEqual(self.request('GET', '/', headers={'Host': 'attacker.example'})[0], 403)

    def test_cross_origin_write_rejected(self):
        headers = {'X-Jarvis-Token': self.token(), 'Origin': 'https://attacker.example', 'Content-Type': 'application/json'}
        self.assertEqual(self.request('POST', '/api/notes', '{}', headers)[0], 403)

    def test_note_roundtrip_through_http(self):
        headers = {'X-Jarvis-Token': self.token(), 'Content-Type': 'application/json'}
        status, data = self.request('POST', '/api/notes', json.dumps({'title': 'HTTP test', 'content': 'Local data'}), headers)
        self.assertEqual(status, 201)
        from urllib.parse import quote
        status, content = self.request('GET', '/api/note?path=' + quote(json.loads(data)['path']), headers=headers)
        self.assertEqual(status, 200)
        self.assertIn('Local data', json.loads(content)['content'])

    def test_invalid_payload_does_not_create_note(self):
        headers = {'X-Jarvis-Token': self.token(), 'Content-Type': 'application/json'}
        self.assertEqual(self.request('POST', '/api/jobs', '[]', headers)[0], 400)

    @unittest.skipUnless(os.name == 'nt', 'Native desktop launcher is Windows only')
    def test_native_launcher_does_not_accept_arbitrary_command(self):
        launcher = Path(self.temp.name) / 'Start-HermesDesktopLocal.ps1'
        launcher.write_text('# Mocked; never executed by this test.', encoding='utf-8')
        headers = {'X-Jarvis-Token': self.token(), 'Content-Type': 'application/json'}
        with patch('server.subprocess.Popen') as process:
            status, _ = self.request('POST', '/api/hermes', '{"command":"UNTRUSTED"}', headers)
        self.assertEqual(status, 202)
        self.assertEqual(process.call_args.args[0], ['powershell.exe', '-NoProfile', '-File', str(launcher)])


if __name__ == '__main__':
    unittest.main(verbosity=2)
