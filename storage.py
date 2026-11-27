"""Conexões dos módulos de conteúdo. SQLite local ou PostgreSQL em produção."""
import os
import sqlite3
import threading
from pathlib import Path

_schema_lock = threading.Lock()
_initialized = set()


class Postgres:
    def __init__(self, db, driver):
        self.db = db
        self.driver = driver

    def execute(self, sql, params=()):
        if sql == 'BEGIN IMMEDIATE':
            # Serializa operações de leitura seguida de gravação (limites de acesso).
            sql = 'SELECT pg_advisory_xact_lock(726184903)'
        try:
            return self.db.execute(sql.replace('?', '%s'), params)
        except self.driver.Error:
            raise sqlite3.DatabaseError('Falha no banco de dados.') from None

    def executemany(self, sql, rows):
        for row in rows:
            self.execute(sql,row)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            if exc_type is None:
                self.db.commit()
            else:
                self.db.rollback()
        except self.driver.Error:
            raise sqlite3.DatabaseError('Falha ao concluir transação.') from None

    def close(self):
        self.db.close()


def connect(path, schema):
    url = os.environ.get('DATABASE_URL','').strip()
    if not url:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(path, timeout=10)
        try:
            db.executescript(schema)
        except BaseException:
            db.close()
            raise
        return db

    try:
        import psycopg
        raw = psycopg.connect(url,connect_timeout=8,options='-c statement_timeout=20000')
    except (ImportError, OSError):
        raise sqlite3.DatabaseError('PostgreSQL indisponível.') from None
    except Exception:
        raise sqlite3.DatabaseError('Falha ao conectar ao PostgreSQL.') from None
    db = Postgres(raw,psycopg)
    try:
        with _schema_lock:
            if (url,schema) not in _initialized:
                ddl = schema.replace('INTEGER PRIMARY KEY AUTOINCREMENT','BIGSERIAL PRIMARY KEY').replace('id INTEGER PRIMARY KEY','id BIGSERIAL PRIMARY KEY').replace(' BLOB ',' BYTEA ').replace(' REAL ',' DOUBLE PRECISION ')
                with db:
                    db.execute('SELECT pg_advisory_xact_lock(726184904)')
                    for statement in ddl.split(';'):
                        if statement.strip(): db.execute(statement)
                _initialized.add((url,schema))
        return db
    except BaseException:
        db.close()
        raise
