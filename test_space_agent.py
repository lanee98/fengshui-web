import io
import json
import os
import unittest
from unittest.mock import patch
from modelscope_app import app


class SpaceAgentTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.headers = {'X-Requested-With': 'ImmerseHome'}

    def test_missing_key_and_validation(self):
        with patch.dict(os.environ, {'ZHIPU_API_KEY': ''}):
            self.assertFalse(self.client.get('/api/space-agent/status').json['configured'])
            self.assertEqual(self.client.post('/api/space-agent/chat', json={'question': '窗台摆什么？'}, headers=self.headers).status_code, 503)
        self.assertEqual(self.client.post('/api/space-agent/chat', json={'question': 'test'}).status_code, 403)
        self.assertEqual(self.client.post('/api/space-agent/chat', json={'question': 'test'}, headers={**self.headers, 'Origin': 'https://evil.example'}).status_code, 403)
        self.assertEqual(self.client.post('/api/space-agent/chat', json={'question': 'x' * 501}, headers=self.headers).status_code, 400)

    def test_online_contract_context_and_secret(self):
        response = io.BytesIO(json.dumps({'choices': [{'message': {'content': '可考虑适合光照的发财树，但不保证财运。'}}]}).encode())
        with patch.dict(os.environ, {'ZHIPU_API_KEY': 'test-secret'}), patch('space_agent.net.urlopen', return_value=response) as send:
            result = self.client.post('/api/space-agent/chat', json={'question': '窗台呢？', 'history': [{'role': 'user', 'content': '我想布置卧室'}], 'context': {'furniture': [{'type': 'bed'}]}}, headers=self.headers)
            self.assertEqual(result.status_code, 200)
            self.assertIn('勿作为决策依据', result.json['answer'])
            self.assertNotIn('test-secret', result.get_data(as_text=True))
            req = send.call_args.args[0]
            self.assertEqual(req.get_header('Authorization'), 'Bearer test-secret')
            self.assertEqual(json.loads(req.data)['messages'][1]['content'], '我想布置卧室')
            self.assertIn('bed', json.loads(req.data)['messages'][-1]['content'])

    def test_failure_is_sanitized(self):
        with patch.dict(os.environ, {'ZHIPU_API_KEY': 'test-secret'}), patch('space_agent.net.urlopen', side_effect=OSError('test-secret')):
            response = self.client.post('/api/space-agent/chat', json={'question': '布置建议'}, headers=self.headers)
            self.assertEqual(response.status_code, 502)
            self.assertNotIn('test-secret', response.get_data(as_text=True))

    def test_modelscope_proxy_origin(self):
        with patch.dict(os.environ, {'ZHIPU_API_KEY': ''}):
            for origin, expected in [
                ('https://lanee98-fengshuipingtai.ms.show', 503),
                ('https://evil.example', 403),
                ('https://lanee98-fengshuipingtai.ms.show.evil.example', 403),
                ('http://lanee98-fengshuipingtai.ms.show', 403),
            ]:
                result = self.client.post('/api/space-agent/chat', base_url='http://container:7860', json={'question': '你好'}, headers={**self.headers, 'Origin': origin})
                self.assertEqual(result.status_code, expected, origin)
