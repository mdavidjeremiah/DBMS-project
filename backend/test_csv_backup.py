import csv
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from sqlalchemy import Column, Integer, MetaData, String, ForeignKey, create_engine, select, Table, DateTime, Numeric, Boolean, LargeBinary
from sqlalchemy.orm import declarative_base, sessionmaker
from csv_backup import create_snapshot, install_backup_hooks, restore_snapshot


class BackupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.engine = create_engine('sqlite:///' + str(self.root / 'source.db'))
        self.base = declarative_base()
        class Record(self.base):
            __tablename__ = 'record'
            id = Column(Integer, primary_key=True)
            value = Column(String, nullable=True)
            parent_id = Column(Integer, ForeignKey('record.id'))
        self.record = Record
        self.base.metadata.create_all(self.engine)
        self.factory = sessionmaker(bind=self.engine)
        self.env = patch.dict(os.environ, {'CSV_BACKUP_DIR': str(self.root / 'backups')})
        self.env.start()
        install_backup_hooks(self.factory, self.engine)

    def tearDown(self):
        self.env.stop()
        self.engine.dispose()
        self.temp.cleanup()

    def latest(self):
        root = self.root / 'backups'
        return root / (root / 'CURRENT').read_text()

    def test_commit_update_delete_and_rollback(self):
        with self.factory() as session:
            session.add(self.record(id=1, value='comma, quote"\nUnicode: Nairobi ✓'))
            session.commit()
            first = self.latest()
            session.get(self.record, 1).value = 'updated'
            session.commit()
            with (self.latest() / 'table-0000.csv').open(encoding='utf-8', newline='') as handle:
                self.assertEqual(list(csv.reader(handle))[1][1], 'updated')
            session.add(self.record(id=2, value='rolled back'))
            session.flush()
            session.rollback()
            previous = self.latest()
            self.assertEqual(previous, self.latest())
            session.delete(session.get(self.record, 1))
            session.commit()
            with (self.latest() / 'table-0000.csv').open(encoding='utf-8', newline='') as handle:
                self.assertEqual(len(list(csv.reader(handle))), 1)

    def test_restore_round_trip_and_refuse_nonempty(self):
        values = [None, '', '\\N', '\\literal', 'comma, "quote"\n✓']
        with self.factory() as session:
            for i, value in enumerate(values, 1):
                session.add(self.record(id=i, value=value, parent_id=1 if i > 1 else None))
            session.commit()
        target = create_engine('sqlite:///' + str(self.root / 'target.db'))
        try:
            self.base.metadata.create_all(target)
            self.assertEqual(restore_snapshot(target, self.latest()), len(values))
            with target.connect() as connection:
                self.assertEqual(connection.execute(select(self.record.value).order_by(self.record.id)).scalars().all(), values)
            with self.assertRaisesRegex(ValueError, 'empty'):
                restore_snapshot(target, self.latest())
        finally:
            target.dispose()

    def test_failed_export_keeps_previous_snapshot_and_commit(self):
        with self.factory() as session:
            session.add(self.record(id=1, value='old'))
            session.commit()
            previous = self.latest()
            with patch('csv_backup.create_snapshot', side_effect=OSError('Disk full')):
                session.add(self.record(id=2, value='saved'))
                session.commit()
            self.assertEqual(previous, self.latest())
            self.assertTrue((self.root / 'backups' / 'last-error.txt').exists())
            self.assertIsNotNone(session.get(self.record, 2))

    def test_broken_relationship_rolls_back_restore(self):
        with self.engine.begin() as connection:
            connection.execute(self.record.__table__.insert(), {'id': 1, 'value': 'orphan', 'parent_id': 999})
        snapshot = create_snapshot(self.engine)
        target = create_engine('sqlite:///' + str(self.root / 'target.db'))
        try:
            self.base.metadata.create_all(target)
            with self.assertRaisesRegex(ValueError, 'Broken relationship'):
                restore_snapshot(target, snapshot)
            with target.connect() as connection:
                self.assertEqual(connection.execute(select(self.record.id)).all(), [])
        finally:
            target.dispose()

    def test_typed_values_and_migration_revision(self):
        from datetime import datetime
        from decimal import Decimal
        metadata = self.base.metadata
        version = Table('alembic_version', metadata, Column('version_num', String, primary_key=True))
        typed = Table('typed', metadata, Column('id', Integer, primary_key=True),
                      Column('amount', Numeric(12, 2)), Column('created', DateTime),
                      Column('enabled', Boolean), Column('payload', LargeBinary))
        metadata.create_all(self.engine)
        expected = {'id': 1, 'amount': Decimal('123.45'), 'created': datetime(2026, 10, 13, 12, 34, 56),
                    'enabled': True, 'payload': b'\x00\xff'}
        with self.engine.begin() as connection:
            connection.execute(version.insert(), {'version_num': 'revision-1'})
            connection.execute(typed.insert(), expected)
        snapshot = create_snapshot(self.engine)
        target = create_engine('sqlite:///' + str(self.root / 'typed-target.db'))
        try:
            metadata.create_all(target)
            with target.begin() as connection:
                connection.execute(version.insert(), {'version_num': 'revision-1'})
            restore_snapshot(target, snapshot)
            with target.connect() as connection:
                self.assertEqual(dict(connection.execute(select(typed)).mappings().one()), expected)
        finally:
            target.dispose()


if __name__ == '__main__':
    unittest.main()
