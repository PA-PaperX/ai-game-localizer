"""Local browser GUI, loopback-only with authenticated APIs and staged writes."""
import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
from pathlib import Path
import secrets
import threading
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit
import webbrowser

from .cli import (LocalizerError, batch, digest, entry, export, import_file,
                  load_project, read_json, save, tokens, validate_for_engine)

ASSETS = Path(__file__).with_name('web')


def now():
    return datetime.now(timezone.utc).isoformat()


def revision(e):
    return digest(json.dumps(e, ensure_ascii=False, sort_keys=True))


def issue(e, engine):
    if e['target'] is None:
        return None
    try:
        validate_for_engine(e['source'], e['target'], engine)
    except LocalizerError as exc:
        return str(exc)
    return None


class Workspace:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.resources = {}
        self.cache = {}
        self.manifest_path = self.root/'workspace.json'
        self.manifest = read_json(self.manifest_path) if self.manifest_path.exists() else {
            'schema': 1, 'title': 'โปรเจกต์แปลเกม', 'brief': {}, 'resources': []}
        self.reload()

    def reload(self):
        self.resources = {}
        self.cache = {}
        for row in self.manifest['resources']:
            if not isinstance(row['id'], str) or len(row['id']) != 16 or any(c not in '0123456789abcdef' for c in row['id']):
                raise LocalizerError('Invalid workspace resource identifier')
            path = (self.root/row['file']).resolve()
            if not path.is_relative_to(self.root):
                raise LocalizerError('Workspace resource path escapes workspace')
            p = load_project(path)
            self.resources[row['id']] = dict(meta=row, path=path, project=p,
                                            disk_hash=hashlib.sha256(path.read_bytes()).hexdigest(),
                                            index={e['id']: e for e in p['entries']})
            self.reindex(row['id'])

    def reindex(self, resource):
        item = self.resources[resource]
        self.cache[resource] = [dict(id=e['id'], resource=resource, status=e['status'],
            source=e['source'], target=e['target'], group=(e['id'].lstrip('/').split('/')[0]
                if '/' in e['id'].lstrip('/') else 'ทั่วไป'),
            issue=issue(e, item['project']['engine']),
            search=(e['id']+'\n'+e['source']+'\n'+(e['target'] or '')).casefold())
            for e in item['project']['entries']]

    def resource(self, resource):
        if resource not in self.resources:
            raise LocalizerError('Unknown resource')
        return self.resources[resource]

    def check_disk(self, item):
        if hashlib.sha256(item['path'].read_bytes()).hexdigest() != item['disk_hash']:
            raise LocalizerError('ไฟล์ถูกแก้จากโปรแกรมอื่น กรุณาเปิด GUI ใหม่ก่อนบันทึก')

    def stats(self):
        resources = []
        counts = Counter()
        problem_count = 0
        for key, item in self.resources.items():
            rows = self.cache[key]
            status = Counter(e['status'] for e in rows)
            counts.update(status)
            problems = sum(bool(e['issue']) for e in rows)
            problem_count += problems
            resources.append(dict(id=key, name=item['meta']['name'], total=len(rows),
                                  reviewed=status['reviewed'], issues=problems))
        total = sum(counts.values())
        return dict(title=self.manifest['title'], total=total, counts=dict(counts), issues=problem_count,
                    reviewed_percent=round(100*counts['reviewed']/total, 2) if total else 0,
                    resources=resources, brief=self.manifest.get('brief', {}))

    def filtered(self, query):
        resource = query.get('resource', 'all')
        rows = self.cache.get(resource, []) if resource != 'all' else [e for group in self.cache.values() for e in group]
        text, status, group = query.get('q', '').casefold(), query.get('status', 'all'), query.get('group', 'all')
        groups = Counter(e['group'] for e in rows)
        result = [e for e in rows if (not text or text in e['search']) and
                  (status == 'all' or status == 'issues' and e['issue'] or e['status'] == status) and
                  (group == 'all' or e['group'] == group)]
        return result, groups

    def listing(self, query):
        rows, groups = self.filtered(query)
        offset = max(0, int(query.get('offset', 0)))
        limit = min(100, max(1, int(query.get('limit', 50))))
        page = [{k:v for k,v in e.items() if k != 'search'} for e in rows[offset:offset+limit]]
        return dict(items=page, total=len(rows), offset=offset, limit=limit, groups=dict(groups))

    def detail(self, resource, key):
        item = self.resource(resource)
        if key not in item['index']:
            raise LocalizerError('Unknown entry')
        e = item['index'][key]
        siblings = item['project']['entries']
        position = next(i for i, candidate in enumerate(siblings) if candidate['id'] == key)
        nearby = [dict(id=s['id'], source=s['source'], target=s['target'])
                  for s in siblings[max(0, position-2):position+3]]
        # File order is only a research aid, never proof of scene continuity.
        try:
            markers = list(tokens(e['source']))
        except LocalizerError:
            markers = []
        return dict(entry=e, revision=revision(e), resource=resource, issue=issue(e, item['project']['engine']),
                    source_lines=e['source'].splitlines(), markers=markers, nearby=nearby)

    def edit(self, data, approve=False):
        with self.lock:
            resource, key = data['resource'], data['id']
            item = self.resource(resource)
            self.check_disk(item)
            if key not in item['index']:
                raise LocalizerError('Unknown entry')
            old = item['index'][key]
            if data.get('revision') != revision(old):
                raise LocalizerError('รายการนี้เปลี่ยนแล้ว กรุณาเปิดใหม่ก่อนบันทึก')
            new = dict(old)
            if 'target' in data:
                if data['target'] is not None:
                    validate_for_engine(old['source'], data['target'], item['project']['engine'])
                new['target'] = data['target']
            if 'context' in data:
                if not isinstance(data['context'], dict):
                    raise LocalizerError('Context must be an object')
                new['context'] = data['context']
            new['status'], new['review'] = ('untranslated' if new['target'] is None else 'draft'), None
            if approve:
                reviewer = str(data.get('reviewer', '')).strip()
                notes = str(data.get('notes', '')).strip()
                context = new.get('context', {})
                if not reviewer or not notes:
                    raise LocalizerError('ระบุผู้ตรวจและบันทึกการตรวจรับ')
                if context.get('translation_readiness') != 'ready' or not context.get('references'):
                    raise LocalizerError('ตรวจบริบทและเพิ่มหลักฐานก่อนตรวจรับคำแปล')
                validate_for_engine(new['source'], new['target'], item['project']['engine'])
                new['status'] = 'reviewed'
                new['review'] = dict(reviewer=reviewer, notes=notes, timestamp=now())
            history = self.root/'history'/resource
            history.mkdir(parents=True, exist_ok=True)
            # Save the old entry before mutating; source/templates are never edited.
            checkpoint = history/(secrets.token_hex(12)+'.json')
            save(checkpoint, dict(id=key, timestamp=now(), entry=old, revision=revision(old)))
            rows = item['project']['entries']
            index = next(i for i,e in enumerate(rows) if e['id'] == key)
            rows[index] = new
            try:
                save(item['path'], item['project'])
            except BaseException:
                rows[index] = old
                raise
            item['index'][key] = new
            item['disk_hash'] = hashlib.sha256(item['path'].read_bytes()).hexdigest()
            self.reindex(resource)
            return self.detail(resource, key)

    def history(self, resource, key):
        self.detail(resource, key)
        folder = self.root/'history'/resource
        rows = []
        if folder.exists():
            for path in folder.glob('*.json'):
                record = read_json(path)
                if record['id'] == key:
                    rows.append(dict(checkpoint=path.stem, timestamp=record['timestamp'],
                                     target=record['entry']['target'], status=record['entry']['status']))
        return sorted(rows, key=lambda r:r['timestamp'], reverse=True)[:10]

    def restore(self, data):
        resource, key = data['resource'], data['id']
        self.resource(resource)
        checkpoint = data['checkpoint']
        if not isinstance(checkpoint, str) or len(checkpoint) != 24 or any(c not in '0123456789abcdef' for c in checkpoint):
            raise LocalizerError('Invalid history checkpoint')
        record = read_json(self.root/'history'/resource/(checkpoint+'.json'))
        if record['id'] != key:
            raise LocalizerError('History entry differs')
        return self.edit(dict(resource=resource, id=key, revision=data['revision'],
                              target=record['entry']['target'], context=record['entry']['context']))

    def import_csv(self, data):
        with self.lock:
            name = str(data.get('name', 'resource.csv'))
            label = Path(name).name
            identifier = secrets.token_hex(8)
            original = self.root/'inputs'/(identifier+'.csv')
            project_path = self.root/'projects'/(identifier+'.json')
            original.parent.mkdir(exist_ok=True)
            content = data.get('content')
            if not isinstance(content, str):
                raise LocalizerError('CSV content must be text')
            original.write_text(content, encoding='utf-8', newline='')
            engine = data.get('engine', 'generic')
            if engine not in ('generic','unreal','unity','godot','renpy','rpgmaker','gamemaker'):
                raise LocalizerError('Unknown engine')
            delimiter = data.get('delimiter', ',')
            if not isinstance(delimiter, str) or len(delimiter) != 1:
                raise LocalizerError('Delimiter must be one character')
            args = SimpleNamespace(input=original, project=project_path, format='csv', engine=engine,
                id_column=data.get('id_column','key'), source_column=data.get('source_column','source'),
                target_column=data.get('target_column','target'), delimiter=delimiter,
                source_language=data.get('source_language','en'), target_language=data.get('target_language','th'))
            import_file(args)
            p = load_project(project_path)
            # Existing targets are imported as drafts, not silently approved.
            t = p['template']
            for e,r in zip(p['entries'], t['rows']):
                target = r.get(t['target_column'])
                if target:
                    e.update(target=target, status='draft')
            save(project_path, p)
            self.manifest['resources'].append(dict(id=identifier, name=label, file='projects/'+identifier+'.json'))
            save(self.manifest_path, self.manifest)
            self.reload()
            return self.stats()

    def make_batch(self, data):
        resource = data['resource']
        item = self.resource(resource)
        output = self.root/'batches'/(resource+'-'+secrets.token_hex(6)+'.json')
        brief = self.root/'brief.json'
        save(brief, self.manifest.get('brief', {}))
        batch(SimpleNamespace(project=item['path'], output=output, limit=min(100, max(1,int(data.get('limit',25)))), brief=brief))
        result = read_json(output)
        result['resource'] = resource
        result['entry_revisions'] = {e['id']: revision(item['index'][e['id']]) for e in result['items']}
        save(output, result)
        return result

    def apply_batch(self, data):
        from .cli import apply
        with self.lock:
            b, result = data['batch'], data['result']
            resource = b.get('resource')
            item = self.resource(resource)
            self.check_disk(item)
            for key, expected in b.get('entry_revisions', {}).items():
                if key not in item['index'] or revision(item['index'][key]) != expected:
                    raise LocalizerError('ชุดงานเก่าแล้ว มีรายการถูกแก้ไขหลังสร้างชุดงาน')
            directory = self.root/'batches'/secrets.token_hex(8)
            directory.mkdir(parents=True)
            b_path, r_path = directory/'request.json', directory/'result.json'
            save(b_path, b); save(r_path, result)
            # Preserve a full project checkpoint for batch changes.
            save(directory/'before.json', item['project'])
            apply(SimpleNamespace(project=item['path'], batch=b_path, result=r_path))
            self.reload()
            return self.stats()

    def export_csv(self, resource):
        item = self.resource(resource)
        dest = self.root/'staging'/(resource+'-'+secrets.token_hex(6)+'.csv')
        export(SimpleNamespace(project=item['path'], output=dest))
        return dest.read_bytes()

    def import_outlast(self, source_root):
        """Opt-in adapter for the private project's layout, never installed game files."""
        root = Path(source_root).resolve()
        marker = str(root)
        if self.manifest.get('legacy_source'):
            if self.manifest['legacy_source'] != marker:
                raise LocalizerError('This workspace already belongs to another legacy project')
            return self.stats()
        if self.manifest['resources']:
            raise LocalizerError('Use an empty GUI workspace for legacy import')
        source_dir = root/'source/exports/en'
        if not source_dir.is_dir():
            raise LocalizerError('Missing original localization exports')
        contexts_path = root/'translations/context-reviewed.json'
        context_rows = read_json(contexts_path).get('entries',[]) if contexts_path.exists() else []
        context_index = {(r.get('file'),r['key'],r.get('source')):r for r in context_rows}
        imported = []
        for source in sorted(source_dir.glob('*.csv')):
            resource = source.stem
            identifier = digest(resource)[:16]
            dest = self.root/'projects'/(identifier+'.json')
            import_file(SimpleNamespace(input=source, project=dest, format='csv', engine='unreal',
                id_column='key', source_column='source', target_column='target', delimiter=',',
                source_language='en', target_language='th'))
            p = load_project(dest)
            drafts_path = root/'translations/full'/(resource+'.th.csv')
            drafts = {}
            if drafts_path.exists():
                with drafts_path.open(encoding='utf-8-sig', newline='') as f:
                    drafts = {r['key']:r for r in csv.DictReader(f)}
            for e in p['entries']:
                candidate = drafts.get(e['id'])
                if candidate and candidate['source'] == e['source']:
                    e['target'] = candidate['target']
                    e['status'] = 'reviewed' if candidate.get('status') == 'reviewed' else 'draft'
                    e['legacy_status'] = candidate.get('status')
                    if e['status'] == 'reviewed':
                        e['review'] = dict(reviewer='PaperX legacy project', notes='Imported existing reviewed snapshot; no new review claimed')
                context = context_index.get((resource,e['id'],e['source']))
                if context:
                    e['context'] = {k:v for k,v in context.items() if k not in ('key','source','target','file','status')}
                    e['context']['translation_readiness'] = 'ready' if context.get('references') else 'pending'
            save(dest, p)
            load_project(dest)
            imported.append(dict(id=identifier, name=resource, file='projects/'+identifier+'.json'))
        self.manifest.update(title='The Outlast Trials', legacy_source=marker, resources=imported,
            brief=dict(game='The Outlast Trials', build='Steam 25334040 / v260801', source_language='en',target_language='th',
                style='Use this project’s character-specific voice guide; research every scene before drafting',
                available_evidence=['Local source exports and legacy contextual review records']))
        save(self.manifest_path, self.manifest)
        self.reload()
        return self.stats()


class Server(ThreadingHTTPServer):
    daemon_threads = True
    def __init__(self, address, workspace):
        self.workspace, self.token = workspace, secrets.token_urlsafe(32)
        super().__init__(address, Handler)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # No tokens, file paths or game dialogue in HTTP logs.

    def send(self, code, data, content_type='application/json; charset=utf-8', download=None):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8') if content_type.startswith('application/json') else data
        self.send_response(code)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Referrer-Policy','no-referrer')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; frame-ancestors 'none'")
        if download:
            self.send_header('Content-Disposition', 'attachment; filename="'+download+'"')
        self.end_headers()
        self.wfile.write(body)

    def authorized(self):
        host = '127.0.0.1:'+str(self.server.server_port)
        if self.headers.get('Host') != host:
            return False
        origin = self.headers.get('Origin')
        if origin and origin != 'http://'+host:
            return False
        supplied = self.headers.get('X-Localizer-Token','')
        return secrets.compare_digest(supplied, self.server.token)

    def do_GET(self):
        path = urlsplit(self.path)
        if path.path.startswith('/api/'):
            if not self.authorized():
                return self.send(403, dict(error='Local session authorization required'))
            q = {k:v[0] for k,v in parse_qs(path.query).items()}
            try:
                w = self.server.workspace
                with w.lock:
                    if path.path == '/api/state': data = w.stats()
                    elif path.path == '/api/entries': data = w.listing(q)
                    elif path.path == '/api/entry': data = w.detail(q['resource'],q['id'])
                    elif path.path == '/api/history': data = w.history(q['resource'],q['id'])
                    else: return self.send(404, dict(error='Unknown route'))
                self.send(200, data)
            except (ValueError, KeyError, TypeError, OSError) as exc:
                self.send(400, dict(error=str(exc)))
        else:
            name = {'/':'index.html','/app.js':'app.js','/app.css':'app.css'}.get(path.path)
            if not name:
                return self.send(404, b'Not found', 'text/plain')
            kind = {'html':'text/html','js':'text/javascript','css':'text/css'}[name.rsplit('.',1)[1]]
            self.send(200, (ASSETS/name).read_bytes(), kind+'; charset=utf-8')

    def do_POST(self):
        if not self.authorized():
            return self.send(403, dict(error='Local session authorization required'))
        try:
            length = int(self.headers.get('Content-Length', 0))
            if not 0 < length <= 32*1024*1024:
                raise LocalizerError('Request size out of range')
            if not self.headers.get('Content-Type','').startswith('application/json'):
                raise LocalizerError('JSON body required')
            data = json.loads(self.rfile.read(length))
            if not isinstance(data,dict):
                raise LocalizerError('Body must be an object')
            w = self.server.workspace
            route = urlsplit(self.path).path
            if route == '/api/edit': result = w.edit(data)
            elif route == '/api/review': result = w.edit(data,approve=True)
            elif route == '/api/restore': result = w.restore(data)
            elif route == '/api/import': result = w.import_csv(data)
            elif route == '/api/batch': result = w.make_batch(data)
            elif route == '/api/apply': result = w.apply_batch(data)
            elif route == '/api/export':
                with w.lock:
                    return self.send(200, w.export_csv(data['resource']), 'text/csv; charset=utf-8','translations.csv')
            else: return self.send(404, dict(error='Unknown route'))
            self.send(200,result)
        except (ValueError, KeyError, TypeError, OSError, AttributeError) as exc:
            self.send(400,dict(error=str(exc)))


def main(argv=None):
    parser = argparse.ArgumentParser(description='AI Game Localizer — local GUI')
    parser.add_argument('--workspace',type=Path,default=Path('work/gui'))
    parser.add_argument('--outlast',type=Path,help='Opt-in import of an existing private Outlast translation workspace')
    parser.add_argument('--port',type=int,default=0)
    parser.add_argument('--no-browser',action='store_true')
    args = parser.parse_args(argv)
    workspace = Workspace(args.workspace)
    if args.outlast:
        workspace.import_outlast(args.outlast)
    server = Server(('127.0.0.1',args.port),workspace)
    url = 'http://127.0.0.1:'+str(server.server_port)+'/#'+server.token
    print('Local GUI: '+url, flush=True)
    print('Close with Ctrl+C. Edits stay in the GUI workspace; installed game files are untouched.',flush=True)
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
