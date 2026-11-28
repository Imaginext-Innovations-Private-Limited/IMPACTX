"""Exercise the installed MySQL connection with a rollback-only private fixture."""
from uuid import uuid4
from navigator.store import db,now
def main():
    owner=uuid4().hex;pid=uuid4().hex
    with db() as c:
        server=c.execute('SELECT VERSION()').fetchone()[0]
        try:
            c.execute('INSERT INTO households VALUES(?,?)',(owner,now()))
            c.execute('INSERT INTO profiles VALUES(?,?,?,?,?,?)',(pid,owner,'Connection check','{}','{}',now()))
            row=c.execute('SELECT id,name FROM profiles WHERE id=? AND owner=?',(pid,owner)).fetchone()
            if row is None or row['id']!=pid or row[1]!='Connection check':raise ValueError('Profile round trip failed.')
        finally:c.connection.rollback()
    print('MySQL',server,'passed a profile write and read. Test records rolled back.')
if __name__=='__main__':main()
