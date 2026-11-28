"""Portable per-laptop launcher. Run inside the environment prepared by setup."""
import argparse
import getpass
import os
from pathlib import Path
import socket
import threading
import webbrowser
from navigator.store import DATA,ROOT,db,init,set_password

def install_bootstrap():
    from importlib.metadata import distribution, PackageNotFoundError
    try:dist=distribution('Bootstrap-Flask')
    except PackageNotFoundError:return False
    import shutil
    target=ROOT/'static'/'vendor';target.mkdir(exist_ok=True)
    for f in dist.files or []:
        path=str(f).replace('\\','/')
        if ('/bootstrap5/' in path or '/bootstrap5.' in path or '/bootstrap5-' in path) and path.split('/')[-1] in ('bootstrap.min.css','bootstrap.bundle.min.js'):
            shutil.copyfile(dist.locate_file(f),target/path.split('/')[-1])
    if not (target/'bootstrap.min.css').is_file():
        for file in dist.files or []:
            if str(file).endswith('bootstrap.min.css'):
                source=Path(dist.locate_file(file))
                if 'Bootstrap v5.' in source.read_text(encoding='utf8',errors='replace')[:500]:
                    shutil.copyfile(source,target/'bootstrap.min.css');break
    return (target/'bootstrap.min.css').is_file()

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--no-browser',action='store_true')
    parser.add_argument('--port',type=int,default=8765)
    parser.add_argument('--reset-admin',action='store_true')
    parser.add_argument('--issue-admin-file', action='store_true')
    args = parser.parse_args()
    if args.issue_admin_file:
        init(issue_new_admin=True)
        print('New Welfare Navigator admin password saved to:', DATA / 'ADMIN_FIRST_LOGIN.txt')
        return
    init()
    install_bootstrap()
    if args.reset_admin:
        first=getpass.getpass('Enter new admin password (12+ characters): ')
        if first!=getpass.getpass('Repeat password: '):raise SystemExit('Passwords differ.')
        with db() as c:set_password(c,first)
        (DATA/'ADMIN_FIRST_LOGIN.txt').unlink(missing_ok=True);print('Admin password updated.');return
    port=args.port
    for attempt in range(12):
        with socket.socket() as probe:
            try:probe.bind(('127.0.0.1',port));break
            except OSError:port+=1
    else:raise SystemExit('No available port in requested range.')
    url=f'http://127.0.0.1:{port}'
    print('Open:',url,'\nMySQL configuration and local asset folder:',DATA,flush=True)
    password_file = DATA / 'ADMIN_FIRST_LOGIN.txt'
    if password_file.is_file():
        print('Admin first-login file:', password_file, flush=True)
    else:
        print('Existing admin account. To generate a new password file, run RESET_ADMIN_WINDOWS.bat.', flush=True)
    if not args.no_browser:threading.Timer(1.4,lambda:webbrowser.open(url)).start()
    import uvicorn
    uvicorn.run('navigator.app:app',host='127.0.0.1',port=port,access_log=False)
if __name__=='__main__':main()
