"""Synthetic GUI workflow and loopback API checks; no real game assets."""
import csv
import io
import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from game_localizer.cli import LocalizerError, load_project, validate_for_engine
from game_localizer.gui import Workspace, Server


class GuiWorkspace(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.w = Workspace(Path(self.temp.name)/'gui')
        self.w.import_csv(dict(name='synthetic.csv', engine='unreal',
            content='key,source,target,metadata\nMenu/open,Open {door},,keep\nhello,"Hello, friend",ไง แก,untouched\n'))
        self.resource = self.w.stats()['resources'][0]['id']

    def tearDown(self):
        self.temp.cleanup()

    def edit(self, key='Menu/open', **kwargs):
        d = self.w.detail(self.resource, key)
        return self.w.edit(dict(resource=self.resource, id=key, revision=d['revision'], **kwargs))

    def test_search_paging_and_groups(self):
        rows = self.w.listing(dict(q='แก'))
        self.assertEqual([e['id'] for e in rows['items']], ['hello'])
        self.assertEqual(rows['groups'], {'Menu': 1, 'ทั่วไป': 1})
        self.assertEqual(self.w.listing(dict(q='OPEN'))['total'], 1)
        self.assertEqual(self.w.listing(dict(offset=1, limit=1))['items'][0]['id'], 'hello')
        self.assertEqual(self.w.listing(dict(status='draft'))['total'], 1)

    def test_invalid_edit_atomic_and_stale_revision(self):
        item = self.w.resource(self.resource)
        before = item['path'].read_bytes()
        old = self.w.detail(self.resource, 'Menu/open')
        with self.assertRaises(LocalizerError):
            self.edit(target='เปิด')
        self.assertEqual(before, item['path'].read_bytes())
        self.edit(target='เปิด {door}')
        with self.assertRaises(LocalizerError):
            self.w.edit(dict(resource=self.resource,id='Menu/open',revision=old['revision'],target='เปิด {door}'))
        self.assertEqual(load_project(item['path'])['template']['rows'][0]['source'], 'Open {door}')

    def test_review_requires_context_and_changes_reset_review(self):
        self.edit(target='เปิด {door}')
        d = self.w.detail(self.resource, 'Menu/open')
        data = dict(resource=self.resource,id='Menu/open',revision=d['revision'],reviewer='Reviewer',notes='Checked')
        with self.assertRaises(LocalizerError):
            self.w.edit(data, approve=True)
        context = dict(scene='door interaction', translation_readiness='ready', references=[dict(uri='synthetic.csv',locator='Menu/open')])
        d = self.edit(context=context)
        data['revision'] = d['revision']
        approved = self.w.edit(data, approve=True)
        self.assertEqual(approved['entry']['status'], 'reviewed')
        self.assertEqual(self.w.stats()['reviewed_percent'], 50)
        self.assertEqual(self.edit(target='เปิดประตู {door}')['entry']['status'], 'draft')

    def test_history_restores_blank_without_approval(self):
        self.edit(target='เปิด {door}')
        checkpoint = self.w.history(self.resource, 'Menu/open')[0]['checkpoint']
        d = self.w.detail(self.resource, 'Menu/open')
        restored = self.w.restore(dict(resource=self.resource,id='Menu/open',revision=d['revision'],checkpoint=checkpoint))
        self.assertIsNone(restored['entry']['target'])
        self.assertEqual(restored['entry']['status'], 'untranslated')
        with self.assertRaises(LocalizerError):
            self.w.restore(dict(resource=self.resource,id='Menu/open',revision=d['revision'],checkpoint='../bad'))

    def test_export_fallback_and_metadata(self):
        self.edit(target='เปิด {door}')
        rows = list(csv.DictReader(io.StringIO(self.w.export_csv(self.resource).decode('utf-8-sig'))))
        self.assertEqual(rows[0]['target'], 'Open {door}')
        self.assertEqual(rows[0]['metadata'], 'keep')
        self.assertEqual(rows[1]['target'], 'ไง แก')

    def test_external_file_edit_is_not_overwritten(self):
        item = self.w.resource(self.resource)
        item['path'].write_bytes(item['path'].read_bytes()+b'\n')
        with self.assertRaises(LocalizerError):
            self.edit(target='เปิด {door}')

    def test_batch_drafts_and_stale_batch_rejection(self):
        b = self.w.make_batch(dict(resource=self.resource,limit=2))
        self.assertIn('before', b['instruction'].lower())
        result = dict(items=[dict(id=e['id'],source_sha256=e['source_sha256'],
            target='เปิด {door}' if e['id']=='Menu/open' else 'ไง แก',context={}) for e in b['items']])
        self.w.apply_batch(dict(batch=b,result=result))
        self.assertEqual(self.w.stats()['counts']['draft'], 2)
        with self.assertRaises(LocalizerError):
            self.w.apply_batch(dict(batch=b,result=result))

    def test_resource_path_cannot_escape_workspace(self):
        self.w.manifest['resources'][0]['file'] = '../outside.json'
        with self.assertRaises(LocalizerError):
            self.w.reload()

    def test_resource_identifier_cannot_escape_history(self):
        self.w.manifest['resources'][0]['id'] = '../history'
        with self.assertRaises(LocalizerError):
            self.w.reload()

    def test_legacy_import_is_a_copy_and_preserves_review_provenance(self):
        root = Path(self.temp.name)/'legacy'
        original = root/'source/exports/en/Pilot.csv'
        original.parent.mkdir(parents=True)
        original.write_text('key,source,target\nMenu/open,Open {door},\n',encoding='utf-8')
        translations = root/'translations/full/Pilot.th.csv'
        translations.parent.mkdir(parents=True)
        translations.write_text('key,source,target,status\nMenu/open,Open {door},เปิด {door},reviewed\n',encoding='utf-8')
        before = {p:p.read_bytes() for p in (original,translations)}
        imported = Workspace(Path(self.temp.name)/'pilot-gui')
        self.assertEqual(imported.import_outlast(root)['counts']['reviewed'],1)
        self.assertEqual(imported.import_outlast(root)['total'],1)
        key = imported.stats()['resources'][0]['id']
        e = imported.detail(key,'Menu/open')['entry']
        self.assertIn('legacy',e['review']['reviewer'])
        self.assertEqual(e['source'],'Open {door}')
        for p,data in before.items():
            self.assertEqual(p.read_bytes(),data)

    def test_formatter_keeps_unreal_engine_data(self):
        source = 'Press `Input:Use` {Count}|plural(one=item,other=items) <b>here</>'
        target = 'กด `Input:Use` {Count}|plural(one=ชิ้น,other=ชิ้น) <b>ตรงนี้</>'
        validate_for_engine(source,target,'unreal')
        for bad in (target.replace('Input:Use','Input:Other'), target.replace('other=', 'few='), target.replace('</>', '')):
            with self.assertRaises(LocalizerError):
                validate_for_engine(source,bad,'unreal')
        with self.assertRaises(LocalizerError):
            validate_for_engine('{n, plural, one {x} other {y}}','{n, plural, one {ก} other {ข}}','unreal')

    def test_http_session_origin_and_input_validation(self):
        server = Server(('127.0.0.1',0),self.w)
        thread = threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        url = 'http://127.0.0.1:'+str(server.server_port)
        try:
            with urlopen(url+'/') as r:
                self.assertIn(b'app.js',r.read())
                self.assertIn("frame-ancestors 'none'",r.headers['Content-Security-Policy'])
            for headers in ({},{'X-Localizer-Token':server.token,'Origin':'https://foreign.example'}):
                with self.assertRaises(HTTPError) as e:
                    urlopen(Request(url+'/api/state',headers=headers))
                self.assertEqual(e.exception.code,403)
            headers = {'X-Localizer-Token':server.token,'Content-Type':'application/json'}
            with urlopen(Request(url+'/api/state',headers=headers)) as r:
                self.assertEqual(json.load(r)['total'],2)
            with self.assertRaises(HTTPError) as e:
                urlopen(Request(url+'/api/edit',data=b'[]',headers=headers))
            self.assertEqual(e.exception.code,400)
            with self.assertRaises(HTTPError) as e:
                urlopen(url+'/workspace.json')
            self.assertEqual(e.exception.code,404)
        finally:
            server.shutdown(); server.server_close(); thread.join()


if __name__ == '__main__':
    unittest.main()
