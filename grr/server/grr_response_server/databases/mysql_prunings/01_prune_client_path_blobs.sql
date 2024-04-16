# 1. Create a temporary table to hold the blob_ids that we want to delete
CREATE TEMPORARY TABLE IF NOT EXISTS blobs_pruning (`hash_id` BINARY(32) NOT NULL, `blob_id` BINARY(32) NOT NULL, offset INTEGER);

# 2. Fetch all the blob_ids for which we do not have any client_path anymore
INSERT INTO blobs_pruning (hash_id,blob_id,offset) SELECT hbr.hash_id,b.blob_id,LOCATE(b.blob_id,hbr.blob_references) FROM blobs AS b JOIN hash_blob_references AS hbr WHERE LOCATE(b.blob_id,hbr.blob_references)!=0 AND hbr.hash_id NOT IN (SELECT sha256 FROM client_path_hash_entries);

# 3. Make sure we avoid pruning blobs that are in use by signed_binary_references
DELETE FROM blobs_pruning WHERE blob_id IN (SELECT b.blob_id FROM blobs AS b JOIN signed_binary_references AS sbr WHERE LOCATE(b.blob_id,sbr.blob_references) > 0);

# 4. Delete the orphaned blobs (blobs that no client_path is pointing to anymore)
DELETE FROM blobs WHERE blob_id IN (SELECT DISTINCT(bp.blob_id) FROM blobs_pruning AS bp JOIN hash_blob_references AS hbr WHERE hbr.hash_id NOT IN (SELECT sha256 FROM client_path_hash_entries) AND bp.blob_id NOT IN (SELECT blob_id FROM blob_encryption_keys) AND bp.blob_id NOT IN (SELECT blob_id FROM yara_signature_references));

# 5. Clean up the hash_blob_references with neither a client_path nor blob anymore
DELETE FROM hash_blob_references WHERE hash_id NOT IN (SELECT sha256 FROM client_path_hash_entries);

# 6. Remove the temporary table
DROP TEMPORARY TABLE blobs_pruning;
