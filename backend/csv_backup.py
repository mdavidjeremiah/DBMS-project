"""Atomic CSV snapshots and transactional restore into an empty schema."""
import argparse
import base64
import csv
import json
import logging
import os
import shutil
import tempfile
import threading
import uuid
from contextlib import contextmanager
from datetime import date, datetime, time, timezone
from decimal import Decimal
from pathlib import Path

from sqlalchemy import MetaData, event, select, text

log = logging.getLogger(__name__)
_local_lock = threading.RLock()


def backup_directory():
    return Path(os.getenv('CSV_BACKUP_DIR', str(Path(__file__).parent / 'backups'))).resolve()


@contextmanager
def backup_lock(root):
    root.mkdir(parents=True, exist_ok=True)
    with _local_lock, (root / '.lock').open('a+b') as handle:
        handle.seek(0)
        handle.write(b'0')
        handle.flush()
        handle.seek(0)
        if os.name == 'nt':
            import msvcrt
            # Blocking Windows lock, retrying beyond msvcrt's short default timeout.
            import time as clock
            while True:
                try:
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError:
                    clock.sleep(0.1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == 'nt':
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def encode(value):
    if value is None:
        return '\\N'
    if isinstance(value, bytes):
        return base64.b64encode(value).decode('ascii')
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, bool):
        return '1' if value else '0'
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    value = str(value)
    return '\\' + value if value.startswith('\\') else value


def decode(value, column):
    if value == '\\N':
        return None
    if value.startswith('\\\\'):
        value = value[1:]
    try:
        kind = column.type.python_type
    except NotImplementedError:
        kind = str
    if kind in (datetime, date, time):
        return kind.fromisoformat(value)
    if kind is bytes:
        return base64.b64decode(value, validate=True)
    if kind is bool:
        if value not in ('0', '1'):
            raise ValueError('Invalid boolean value')
        return value == '1'
    if kind in (dict, list):
        return json.loads(value)
    return kind(value)


def create_snapshot(engine, directory=None):
    root = Path(directory) if directory else backup_directory()
    with backup_lock(root):
        staging = Path(tempfile.mkdtemp(prefix='.pending-', dir=root))
        try:
            manifest = {'version': 1, 'created_at': datetime.now(timezone.utc).isoformat(), 'tables': {}}
            with engine.connect() as connection:
                if engine.dialect.name == 'mysql':
                    connection = connection.execution_options(isolation_level='REPEATABLE READ')
                with connection.begin():
                    if engine.dialect.name == 'mysql':
                        connection.execute(text('START TRANSACTION WITH CONSISTENT SNAPSHOT'))
                    metadata = MetaData()
                    metadata.reflect(bind=connection)
                    for name, table in sorted(metadata.tables.items()):
                        filename = f'table-{len(manifest["tables"]):04d}.csv'
                        columns = list(table.columns.keys())
                        count = 0
                        with (staging / filename).open('w', newline='', encoding='utf-8') as handle:
                            writer = csv.writer(handle)
                            writer.writerow(columns)
                            for row in connection.execute(select(table)):
                                writer.writerow([encode(value) for value in row])
                                count += 1
                        manifest['tables'][name] = {'file': filename, 'columns': columns, 'rows': count}
            (staging / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
            generation = 'snapshot-' + uuid.uuid4().hex
            final = root / generation
            staging.rename(final)
            pointer = root / ('.current-' + uuid.uuid4().hex)
            pointer.write_text(generation, encoding='utf-8')
            os.replace(pointer, root / 'CURRENT')
            # Keep the latest complete snapshot; publication happens before cleanup.
            for old in root.glob('snapshot-*'):
                if old != final and old.is_dir():
                    shutil.rmtree(old)
            (root / 'last-error.txt').unlink(missing_ok=True)
            return final
        finally:
            if staging.exists():
                shutil.rmtree(staging)


def install_backup_hooks(factory, engine):
    @event.listens_for(factory, 'before_commit')
    def mark_commit(session):
        if not session.in_nested_transaction():
            session.info['csv_backup_needed'] = True

    @event.listens_for(factory, 'after_rollback')
    def discard(session):
        session.info.pop('csv_backup_needed', None)

    @event.listens_for(factory, 'after_commit')
    def save(session):
        if session.in_nested_transaction() or not session.info.pop('csv_backup_needed', False):
            return
        try:
            create_snapshot(engine)
        except Exception as exc:
            # The database already committed: never report the record as unsaved.
            log.exception('Database committed but CSV backup failed')
            try:
                root = backup_directory()
                root.mkdir(parents=True, exist_ok=True)
                (root / 'last-error.txt').write_text(str(exc), encoding='utf-8')
            except OSError:
                log.exception('Unable to persist CSV backup failure status')


def restore_snapshot(engine, snapshot):
    snapshot = Path(snapshot).resolve()
    manifest = json.loads((snapshot / 'manifest.json').read_text(encoding='utf-8'))
    if manifest.get('version') != 1:
        raise ValueError('Unsupported backup version')
    with engine.connect() as connection:
        with connection.begin():
            metadata = MetaData()
            metadata.reflect(bind=connection)
            if set(metadata.tables) != set(manifest['tables']):
                raise ValueError('Target schema must match the backup; apply the project migrations first')
            for table in metadata.tables.values():
                if table.name == 'alembic_version':
                    info = manifest['tables'][table.name]
                    source = (snapshot / info['file']).resolve()
                    if source.parent != snapshot:
                        raise ValueError('Invalid CSV path')
                    with source.open(newline='', encoding='utf-8') as handle:
                        rows = list(csv.reader(handle))
                    actual = {tuple(encode(value) for value in row) for row in connection.execute(select(table))}
                    if rows[0] != list(table.columns.keys()) or actual != {tuple(row) for row in rows[1:]}:
                        raise ValueError('Target migration revision must match the backup')
                    continue
                if connection.execute(select(table).limit(1)).first() is not None:
                    raise ValueError('Restore requires an empty database; existing records will not be overwritten')
            mysql = engine.dialect.name == 'mysql'
            if mysql:
                connection.execute(text('SET FOREIGN_KEY_CHECKS=0'))
            elif engine.dialect.name == 'sqlite':
                connection.execute(text('PRAGMA defer_foreign_keys=ON'))
            try:
                for name, info in manifest['tables'].items():
                    if name == 'alembic_version':
                        continue
                    table = metadata.tables[name]
                    source = (snapshot / info['file']).resolve()
                    if source.parent != snapshot:
                        raise ValueError('Invalid CSV path')
                    count = 0
                    with source.open(newline='', encoding='utf-8') as handle:
                        reader = csv.reader(handle)
                        if next(reader) != list(table.columns.keys()) or info['columns'] != list(table.columns.keys()):
                            raise ValueError(f'Column mismatch for {name}')
                        batch = []
                        for row in reader:
                            if len(row) != len(table.columns):
                                raise ValueError(f'Invalid CSV row in {name}')
                            batch.append({column.name: decode(value, column) for column, value in zip(table.columns, row)})
                            count += 1
                            if len(batch) == 500:
                                connection.execute(table.insert(), batch)
                                batch = []
                        if batch:
                            connection.execute(table.insert(), batch)
                    if count != info['rows']:
                        raise ValueError(f'Row count mismatch for {name}')
                # MySQL does not validate old rows when foreign-key checks resume.
                for table in metadata.tables.values():
                    for constraint in table.foreign_key_constraints:
                        elements = list(constraint.elements)
                        parent = elements[0].column.table.alias()
                        match = [element.parent == parent.c[element.column.name] for element in elements]
                        from sqlalchemy import and_
                        orphan = select(table).select_from(table.outerjoin(parent, and_(*match))).where(
                            and_(*(element.parent.is_not(None) for element in elements)),
                            parent.c[elements[0].column.name].is_(None),
                        ).limit(1)
                        if connection.execute(orphan).first() is not None:
                            raise ValueError(f'Broken relationship in {table.name}')
            finally:
                if mysql:
                    connection.execute(text('SET FOREIGN_KEY_CHECKS=1'))
    return sum(info['rows'] for info in manifest['tables'].values())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Export CSV backups or restore into an empty database')
    parser.add_argument('action', choices=['export', 'restore'])
    parser.add_argument('--snapshot', help='Snapshot folder containing manifest.json and CSV files')
    parser.add_argument('--database-url', help='Target database URL (defaults to DATABASE_URL)')
    args = parser.parse_args()
    from database import engine as default_engine
    from sqlalchemy import create_engine
    target = create_engine(args.database_url) if args.database_url else default_engine
    if args.action == 'export':
        print(create_snapshot(target))
    else:
        if not args.snapshot:
            parser.error('restore requires --snapshot')
        print(f'Restored {restore_snapshot(target, args.snapshot)} records')
