UPDATE clients SET last_snapshot_timestamp=NULL, last_startup_timestamp=NULL, last_crash_timestamp=NULL WHERE last_ping < (NOW() - INTERVAL 15 DAY);
DELETE FROM clients WHERE last_ping < (NOW() - INTERVAL 15 DAY);
