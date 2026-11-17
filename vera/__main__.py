"""Vera v0.1 command-line proof of concept."""
from __future__ import annotations
import argparse
import json
import os
import sqlite3
from pathlib import Path
from .db import connect, insert_memory, list_memories, get_memories
from .retrieval import retrieve, format_context
from .conversation import Conversation

DEFAULT_DB = Path(os.environ.get('VERA_DB', 'data/vera.sqlite3'))
DEFAULT_MODEL = os.environ.get('VERA_MODEL', 'qwen3:4b')
DEFAULT_URL = os.environ.get('OLLAMA_URL', 'http://127.0.0.1:11434')


def load_json(con, path):
    records = json.loads(Path(path).read_text(encoding='utf8'))
    if not isinstance(records, list):
        raise ValueError('Import file must contain a JSON array')
    added = []
    with con:
        for m in records:
            mem_id = insert_memory(con, title=m['title'], contributor=m['contributor'],
                                   kind=m.get('kind','story'), content=m['content'],
                                   media_path=m.get('media_path'), metadata=m.get('metadata'), commit=False)
            added.append(mem_id)
    print(f'Imported {len(added)} attributed source notes.')



def main():
    parser = argparse.ArgumentParser(description='Offline source-grounded Vera memory engine')
    parser.add_argument('--db', type=Path, default=DEFAULT_DB)
    parser.add_argument('--model', default=DEFAULT_MODEL)
    parser.add_argument('--ollama-url', default=DEFAULT_URL)
    sub = parser.add_subparsers(dest='command',required=True)
    sub.add_parser('init',help='Create local private database')
    sub.add_parser('list',help='List contributed memories')
    show = sub.add_parser('show',help='Show original wording, provenance and media link')
    show.add_argument('id', type=int)
    sub.add_parser('seed-demo',help='Load synthetic memories for first demo; only once')
    sub.add_parser('chat',help='Interactive locally inferred text conversation')
    add = sub.add_parser('add',help='Add an attributed memory')
    for arg in ('title','contributor','content'):
        add.add_argument(f'--{arg}', required=True)
    add.add_argument('--kind', default='story',
                     choices=['story','photo_note','recording_note','letter','recipe','other'])
    add.add_argument('--media-path', default=None)
    import_cmd = sub.add_parser('import-json',help='Import a JSON array of memories')
    import_cmd.add_argument('file', type=Path)
    one = sub.add_parser('ask',help='Ask a single memory question')
    one.add_argument('question')
    args = parser.parse_args()
    con = connect(args.db)
    if args.command == 'init':
        print(f'Private Vera database ready: {args.db.resolve()}')
    elif args.command == 'list':
        for m in list_memories(con):
            print(f'#{m["id"]} [{m["kind"]}] {m["title"]} - {m["contributor"]}')
    elif args.command == 'show':
        print(format_context(get_memories(con, [args.id])) or 'No active contribution with that ID.')
    elif args.command == 'seed-demo':
        if list_memories(con):
            print('Database already contains memories. Demo import skipped to prevent duplicates.')
        else:
            load_json(con, Path(__file__).parent.parent / 'samples/demo_memories.json')
    elif args.command == 'add':
        session = Conversation(con)
        print(session.propose(dict(title=args.title, contributor=args.contributor,
                                   kind=args.kind, content=args.content, media_path=args.media_path)))
        try:
            print(session.respond(input('Confirmation: ').strip()))
        except EOFError:
            print('Not saved.')
    elif args.command == 'import-json':
        records = json.loads(args.file.read_text(encoding='utf8'))
        print(json.dumps(records, ensure_ascii=False, indent=2))
        try:
            confirmed = input('Import these contributions? Type /confirm: ').strip() == '/confirm'
        except EOFError:
            confirmed = False
        if confirmed:
            load_json(con,args.file)
        else:
            print('Import cancelled.')
    elif args.command == 'ask':
        print('Vera:', Conversation(con, args.model, args.ollama_url).respond(args.question))
    elif args.command == 'chat':
        print('Vera text prototype. Type /quit to exit. Family details come only from the local archive.')
        session = Conversation(con, args.model, args.ollama_url)
        while True:
            try:
                question=input('You: ').strip()
            except (EOFError,KeyboardInterrupt):
                break
            if not question:
                continue
            if question.lower() in ('/quit','/exit'):
                break
            try:
                print('Vera:', session.respond(question))
            except (RuntimeError, ValueError, KeyError, TypeError, sqlite3.Error) as exc:
                print(f'Error: {exc}')
    con.close()

if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, ValueError, OSError, KeyError, TypeError, sqlite3.Error) as exc:
        import sys
        print(f'Error: {exc}', file=sys.stderr)
        raise SystemExit(1)
