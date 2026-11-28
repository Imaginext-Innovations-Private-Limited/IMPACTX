"""Local MySQL 8 connection and dictionary rows with positional access."""
import json
import pymysql

class Row(dict):
    def __getitem__(self, key):
        return tuple(self.values())[key] if isinstance(key, int) else super().__getitem__(key)

class Cursor(pymysql.cursors.DictCursor):
    dict_type = Row

class Database:
    def __init__(self, data):
        path = data / 'mysql.json'
        if not path.exists():
            raise RuntimeError('Run SETUP_MYSQL.bat before starting the project.')
        config = json.loads(path.read_text(encoding='utf8'))
        self.connection = pymysql.connect(**config, charset='utf8mb4', cursorclass=Cursor, autocommit=False)

    def execute(self, sql, args=()):
        cur = self.connection.cursor()
        cur.execute(sql.replace('?', '%s'), args or None)
        return cur

    def commit(self):
        self.connection.commit()
