"""Create the application database using a local MySQL administrator account."""
import getpass
import json
import secrets
import os
from navigator.store import DATA
import pymysql

def main():
    DATA.mkdir(parents=True,exist_ok=True)
    path=DATA/'mysql.json'
    if path.exists():
        from navigator.store import init
        init()
        print('Existing configuration checked.')
        return
    port=int(input('Local MySQL port [3306]: ') or 3306)
    user=input('Local MySQL administrator [root]: ') or 'root'
    password=getpass.getpass('MySQL administrator password: ')
    conn=pymysql.connect(host='127.0.0.1',port=port,user=user,password=password,autocommit=True)
    app_user='wf_'+secrets.token_hex(6)
    config=dict(host='127.0.0.1',port=port,user=app_user,password=secrets.token_urlsafe(32),database='welfare_navigator')
    with conn,conn.cursor() as c:
        c.execute('CREATE DATABASE IF NOT EXISTS welfare_navigator CHARACTER SET utf8mb4 COLLATE utf8mb4_bin')
        c.execute("CREATE USER %s@'localhost' IDENTIFIED BY %s",(app_user,config['password']))
        c.execute("GRANT ALL ON welfare_navigator.* TO %s@'localhost'",(app_user,))
    with os.fdopen(os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600),'w',encoding='utf8') as f:json.dump(config,f)
    from navigator.store import init
    init()
    print('MySQL connected and project tables initialized.')
if __name__=='__main__':main()
