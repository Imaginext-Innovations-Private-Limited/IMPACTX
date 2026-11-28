"""Local durable store, migration, immutable policy versions and private profiles."""
import hashlib
import json
import os
import secrets
import tempfile

from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = Path(os.environ.get("WELFARE_DATA", ROOT / "local_data")).resolve()
DEFAULT = {"chat_model":"qwen2.5:3b","embed_model":"bge-m3","ollama_port":11434,"top_k":3,"retention_days":90,"states":["Andhra Pradesh","Telangana","Karnataka"],"languages":["en","te","hi"],"review_days":365}
def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
def dump(value):
    return json.dumps(value,ensure_ascii=False,separators=(",",":"))
def load_file(name):
    return json.loads((ROOT/"seed"/(name+".json")).read_text(encoding="utf-8"))
def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()
@contextmanager
def db():
    DATA.mkdir(mode=0o700,parents=True,exist_ok=True)
    from .mysql_store import Database
    conn=Database(DATA)
    try:
        yield conn
        conn.commit()
    except BaseException:
        conn.connection.rollback()
        raise
    finally:
        conn.connection.close()
def rows(conn,sql,args=()):
    return [dict(r) for r in conn.execute(sql,args)]
def settings(conn):
    row=conn.execute("SELECT value FROM config WHERE id='settings'").fetchone()
    config={**DEFAULT,**(json.loads(row[0]) if row else {})}
    config['states']=list(dict.fromkeys([*config['states'],'Karnataka']))
    return config
def audit(conn,kind,entity="",detail=""):
    conn.execute("INSERT INTO events(time,kind,entity,detail) VALUES(?,?,?,?)",(now(),kind,str(entity)[:100],str(detail)[:400]))
def policy(conn):
    return [json.loads(r[0]) for r in conn.execute("SELECT body FROM schemes WHERE status='published' ORDER BY sid")]
def evidence(conn,sid=None):
    src=rows(conn,"SELECT body FROM sources WHERE active=1"+(" AND sid=?" if sid else "")+" ORDER BY id",(sid,) if sid else ())
    return [json.loads(r['body']) for r in src]
def insert_source(conn,s,active):
    s=dict(s);s.setdefault("version",1);s.setdefault("effective","");s["checksum"]=digest(s["text"])
    conn.execute("INSERT INTO sources(id,sid,body,active) VALUES(?,?,?,?)",(s["id"],s["scheme"],dump(s),int(active)))
def password_hash(password,salt):
    return hashlib.pbkdf2_hmac("sha256",password.encode(),bytes.fromhex(salt),400000).hex()
def set_password(conn,password):
    if len(password)<12: raise ValueError("Use at least 12 characters.")
    salt=secrets.token_hex(16)
    conn.execute("REPLACE INTO config VALUES('password',?)",(salt+":"+password_hash(password,salt),))
    conn.execute("UPDATE sessions SET admin_until=''")
def issue_admin_password(conn):
    """Issue a first-login credential. The caller holds the database initialization lock."""
    password = secrets.token_urlsafe(20)
    path = DATA / 'ADMIN_FIRST_LOGIN.txt'
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf8', dir=DATA, delete=False) as staged:
        temporary = Path(staged.name)
        try:
            staged.write(password + '\n')
            staged.flush()
            os.fsync(staged.fileno())
        except BaseException:
            staged.close()
            temporary.unlink(missing_ok=True)
            raise
    try:
        set_password(conn, password)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return path

def init(*, issue_new_admin=False):
    with db() as c:
        for statement in (ROOT/'navigator'/'schema.sql').read_text().split(';'):
            if statement.strip():c.execute(statement)
        if c.execute("SELECT GET_LOCK('welfare_catalogue_init',30)").fetchone()[0]!=1:
            raise RuntimeError('Another process is initializing the database. Retry startup.')
        if not c.execute("SELECT 1 FROM config WHERE id='seed'").fetchone():
            for s in load_file("schemes"):
                c.execute("INSERT INTO schemes(sid,version,status,body) VALUES(?,1,'published',?)",(s["id"],dump(s)))
            for e in load_file("sources"): insert_source(c,e,True)
            c.execute("INSERT INTO config VALUES('seed','1')")
            audit(c,"Initial source catalogue installed")
        if not c.execute("SELECT 1 FROM config WHERE id='ka_directory'").fetchone():
            for entry in load_file('karnataka_directory'):
                c.execute("INSERT INTO karnataka_directory VALUES(?,?,?,?,?,?,?)",tuple(entry.get(k,'') for k in ('id','name','kind','department','url','official','scheme')))
            c.execute("INSERT INTO config VALUES('ka_directory','1')")
        if issue_new_admin or not c.execute("SELECT 1 FROM config WHERE id='password'").fetchone():
            issue_admin_password(c)
def trace(c,route,steps):
    c.execute("INSERT INTO traces(time,route,body) VALUES(?,?,?)",(now(),route,dump(steps)))
def cleanup(c):
    cutoff=(datetime.now(timezone.utc)-timedelta(days=settings(c)["retention_days"])).isoformat()
    c.execute("DELETE FROM sessions WHERE seen<?",(cutoff,))
    c.execute('DELETE FROM visits WHERE expires<=?',(now(),))
    c.execute('DELETE FROM profiles WHERE updated<?',(cutoff,))
    for table in ["events","traces","experiments"]:
        c.execute(f"DELETE FROM {table} WHERE time<?",(cutoff,))

