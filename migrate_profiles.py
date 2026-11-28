"""Import private records from an old SQLite file; keep each legacy member separate."""
import argparse
import json
import secrets
import sqlite3
from pathlib import Path
from navigator.store import DATA,db,digest,now,init,dump

def migrate(source):
    if not source.is_file():raise ValueError('Select the old navigator.sqlite3 file.')
    init()
    legacy=sqlite3.connect(source.resolve().as_uri()+'?mode=ro',uri=True)
    legacy.row_factory=sqlite3.Row
    out=DATA/('imported-family-codes-'+secrets.token_hex(6)+'.txt')
    try:
        legacy.execute('BEGIN')
        with db() as c,out.open('x',encoding='utf8') as codes:
            out.chmod(0o600)
            for p in legacy.execute('SELECT * FROM profiles'):
                pid=p['id']
                if c.execute('SELECT id FROM profiles WHERE id=?',(pid,)).fetchone():continue
                secret=secrets.token_urlsafe(16);family=digest(secret)
                c.execute('INSERT INTO households VALUES(?,?)',(family,now()))
                c.execute('INSERT INTO profiles VALUES(?,?,?,?,?,?)',(pid,family,p['name'],p['answers'],p['prefs'],now()))
                codes.write(p['name']+' ['+pid[-4:]+']  '+secret+'\n')
                for table,columns in [('drafts','profile,sid,body,updated'),('decisions','profile,sid,body,time'),('reminders','profile,signature,body,wake,dismissed'),('feedback','profile,rating,time')]:
                    for record in legacy.execute(f'SELECT {columns} FROM {table} WHERE profile=?',(pid,)):
                        placeholders=','.join('?' for _ in record)
                        c.execute(f'INSERT INTO {table}({columns}) VALUES({placeholders})',tuple(record))
                        if table=='drafts':
                            saved=json.loads(record['body'])
                            for i,label in enumerate(dict.fromkeys([*saved.get('ready',[]),*saved.get('missing',[])])):
                                c.execute('INSERT INTO checklist_items VALUES(?,?,?,?,?)',(pid,record['sid'],i,label,int(label in saved.get('ready',[]))))
            codes.flush()
    except BaseException:
        out.unlink(missing_ok=True);raise
    finally:legacy.close()
    print('Private recovery codes for newly imported members:',out)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path)
    migrate(parser.parse_args().source)
