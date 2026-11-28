"""Local administrative recovery for large content backups. Run from the project folder."""
import argparse,getpass,hmac,json
from pathlib import Path
from navigator.store import db,init,password_hash,settings
from navigator.ops import backup,restore
from navigator.ai import model_health,build_index
def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['backup','restore','health','reindex']);p.add_argument('file',nargs='?');args=p.parse_args();init()
    with db() as c:
        if args.action=='health':
            print(json.dumps(model_health(settings(c)),indent=2));return
        salt,actual=c.execute("SELECT value FROM config WHERE id='password'").fetchone()[0].split(':')
        if not hmac.compare_digest(actual,password_hash(getpass.getpass('Local admin password: '),salt)):raise SystemExit('Incorrect password.')
        if args.action=='reindex':print(build_index());return
        if not args.file:raise SystemExit('Supply a backup JSON path.')
        path=Path(args.file)
        if args.action=='backup':
            with path.open('x',encoding='utf8') as f:json.dump(backup(c),f,ensure_ascii=False)
        elif input('Type RESTORE to replace policy content on this laptop: ')=='RESTORE':
            c.execute("SELECT value FROM config WHERE id='seed' FOR UPDATE");restore(c,json.loads(path.read_text(encoding='utf8')))
if __name__=='__main__':main()
