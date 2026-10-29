# Applying the database additions

Take a verified backup and test a restored copy first. From backend run `alembic upgrade head`. Revision 0011 creates stock_transaction_log, stock quality/logging triggers, vw_inventory_position and vw_trial_balance. MySQL requires CREATE VIEW and TRIGGER privileges. The MySQL path has not been exercised locally.

Do not stamp an old database to a new revision without comparing its actual schema. The existing migration baseline still depends on current metadata and needs replacement with a frozen baseline before reliable long-term upgrades.

Inspect recovery settings on MySQL with `SHOW VARIABLES WHERE Variable_name IN ('log_bin','binlog_format','innodb_flush_log_at_trx_commit','sync_binlog')`. InnoDB redo/undo support transactions; binary logs support replication and point-in-time recovery when enabled and retained. This change does not alter server configuration.
