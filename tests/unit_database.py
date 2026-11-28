"""Test-only relational stand-in. Production always opens MySQL."""
import sqlite3
import re
from unittest.mock import patch

class UnitDatabase:
    def __init__(self,data):
        self.connection=sqlite3.connect(data/'fixtures.db')
        self.connection.row_factory=sqlite3.Row
        self.connection.execute('PRAGMA foreign_keys=ON')
    def execute(self,sql,args=()):
        if sql.startswith('SELECT GET_LOCK'):return self.connection.execute('SELECT 1')
        sql=sql.replace('BIGINT AUTO_INCREMENT PRIMARY KEY','INTEGER PRIMARY KEY').replace(' STORED UNIQUE',' STORED UNIQUE')
        sql=sql.replace('INSERT IGNORE','INSERT OR IGNORE').replace(' FOR UPDATE','')
        sql=sql.replace('ON DUPLICATE KEY UPDATE body=VALUES(body),updated=VALUES(updated)','ON CONFLICT(profile,sid) DO UPDATE SET body=excluded.body,updated=excluded.updated')
        sql=re.sub(r'JSON_UNQUOTE\((json_extract\([^)]+\))\)',r'\1',sql,flags=re.I)
        return self.connection.execute(sql,args)
    def commit(self):self.connection.commit()

def isolated(case):
    mocked=patch('navigator.mysql_store.Database',UnitDatabase)
    mocked.start()
    case.addCleanup(mocked.stop)
