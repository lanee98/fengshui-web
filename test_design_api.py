import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from flask import Flask

sys.path.insert(0,str(Path(__file__).parent/'webapp'))
from app import app, placement_error, run_audit
from designs import create_design, THEMES
from aholo import install_aholo, AholoClient, ProviderError

class TemplateTests(unittest.TestCase):
    def test_all_template_sizes_preserve_non_overlapping_geometry(self):
        for case in THEMES:
            for width in (3.2,3.5,3.6,4,6):
                for depth in (3.4,3.8,7):
                    for desk in (False,True):
                        scene=create_design(case,width,depth,desk)
                        for item in scene['furniture']:
                            self.assertIsNone(placement_error(scene,item),(case,width,depth,desk,item['name']))
                        self.assertEqual(scene['meta']['template_case'],case)
                        self.assertTrue(scene['furniture'][0]['referenceAssetId'])
                        self.assertEqual(run_audit(scene)['rule_count'],20)

    def test_design_api_and_rejected_dimensions(self):
        client=app.test_client()
        self.assertEqual(client.post('/api/design',json={'case':'L01','width':3.6,'depth':3.8}).status_code,200)
        self.assertEqual(client.post('/api/design',json={'case':'L01','width':1,'depth':3.8}).status_code,400)
        self.assertEqual(client.post('/api/design',json=[]).status_code,400)
        for path in ('/design','/furniture-materials.js','/cloud-models.js','/render-enhancements.js','/reference-pack/catalog.json'):
            response=client.get(path)
            self.assertEqual(response.status_code,200,path)
            response.close()

class CloudContractTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.root=Path(self.temp.name)
        (self.root/'instance').mkdir()
        ref=self.root/'static/reference-pack'
        ref.mkdir(parents=True)
        (ref/'sample.png').write_bytes(b'fake-image-for-contract-test')
        (ref/'catalog.json').write_text(json.dumps({'cases':[{'objects':[{'id':'sample-bed','label':'bed','image':'/reference-pack/sample.png'}]}]}),encoding='utf-8')
        self.app=Flask('cloud_test',root_path=str(self.root),static_folder=str(self.root/'static'))
        install_aholo(self.app)
        self.client=self.app.test_client()
        self.headers={'X-Requested-With':'ImmerseHome'}

    def tearDown(self):
        self.temp.cleanup()

    def test_invalid_assets_are_not_forwarded(self):
        for body in ({'assetId':'../../file'},{'assetId':[]},[]):
            self.assertEqual(self.client.post('/api/aholo/tasks',json=body,headers=self.headers).status_code,400)
        self.assertEqual(self.client.post('/api/aholo/tasks',json={'assetId':'sample-bed'}).status_code,403)

    def test_task_creation_is_deduplicated_and_does_not_expose_key(self):
        provider=self.app.extensions['aholo']
        with patch.dict(os.environ,{'AHOLO_API_KEY':'unit-test-key'}),patch.object(provider,'upload',return_value='https://qhstaticssl.kujiale.com/test.png') as upload,patch.object(provider,'call',return_value={'c':'0','d':12345}) as create:
            first=self.client.post('/api/aholo/tasks',json={'assetId':'sample-bed'},headers=self.headers)
            second=self.client.post('/api/aholo/tasks',json={'assetId':'sample-bed'},headers=self.headers)
            self.assertEqual(first.status_code,202)
            self.assertEqual(second.json['taskId'],'12345')
            self.assertEqual(upload.call_count,1)
            self.assertEqual(create.call_count,1)
            self.assertTrue(create.call_args.args[1]['enablePbr'])
            self.assertNotIn('unit-test-key',self.client.get('/api/aholo/status').get_data(as_text=True))
        with patch.object(provider,'call',return_value={'c':'0','d':{'status':4}}):
            self.assertEqual(self.client.get('/api/aholo/tasks/sample-bed').json['status'],'failed')

    def test_auth_header_matches_official_api(self):
        provider=AholoClient()
        with patch.dict(os.environ,{'AHOLO_API_KEY':'unit-test-key'}),patch.object(provider,'fetch',return_value={'c':'0','d':[]}) as fetch:
            provider.call('/lux3d/v1/generate/task/list?page=1&pagesize=1')
            self.assertEqual(fetch.call_args.args[2]['Authorization'],'unit-test-key')

    def test_failure_text_does_not_echo_upstream_credentials(self):
        from urllib.error import HTTPError
        with patch('aholo.net.urlopen',side_effect=HTTPError('https://api.aholo3d.cn/',401,'private-secret',{},None)):
            with self.assertRaisesRegex(ProviderError,'401') as caught:
                AholoClient.fetch('https://api.aholo3d.cn/')
            self.assertNotIn('private-secret',str(caught.exception))

if __name__=='__main__': unittest.main()
