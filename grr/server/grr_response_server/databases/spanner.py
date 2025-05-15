# Imports the Google Cloud Client Library.
from google.cloud import spanner

from grr_response_core.lib import rdfvalue
from grr_response_server.databases import db as abstract_db
from grr_response_server.databases import spanner_artifacts
from grr_response_server.databases import spanner_blob_keys
from grr_response_server.databases import spanner_blob_references
from grr_response_server.databases import spanner_clients
from grr_response_server.databases import spanner_cron_jobs
from grr_response_server.databases import spanner_events
from grr_response_server.databases import spanner_flows
from grr_response_server.databases import spanner_foreman_rules
from grr_response_server.databases import spanner_hunts
from grr_response_server.databases import spanner_paths
from grr_response_server.databases import spanner_signed_binaries
from grr_response_server.databases import spanner_signed_commands
from grr_response_server.databases import spanner_users
from grr_response_server.databases import spanner_utils
from grr_response_server.databases import spanner_yara
from grr_response_server.models import blobs as models_blobs
from grr_response_server.rdfvalues import objects as rdf_objects

class SpannerDB(
    spanner_artifacts.ArtifactsMixin,
    spanner_blob_keys.BlobKeysMixin,
    spanner_blob_references.BlobReferencesMixin,
    spanner_clients.ClientsMixin,
    spanner_signed_commands.SignedCommandsMixin,
    spanner_cron_jobs.CronJobsMixin,
    spanner_events.EventsMixin,
    spanner_flows.FlowsMixin,
    spanner_foreman_rules.ForemanRulesMixin,
    spanner_hunts.HuntsMixin,
    spanner_paths.PathsMixin,
    spanner_signed_binaries.SignedBinariesMixin,
    spanner_users.UsersMixin,
    spanner_yara.YaraMixin,
    abstract_db.Database,
):
  """A Spanner implementation of the GRR database."""

  def __init__(self, db: spanner_utils.Database) -> None:
    """Initializes the database."""
    self.db = db
    self._write_rows_batch_size = 10000

  def Now(self) -> rdfvalue.RDFDatetime:
    """Retrieves current time as reported by the database."""
    (timestamp,) = self.db.QuerySingle("SELECT CURRENT_TIMESTAMP()")
    return rdfvalue.RDFDatetime.FromDatetime(timestamp)

  def MinTimestamp(self) -> rdfvalue.RDFDatetime:
    """Returns minimal timestamp allowed by the DB."""
    return rdfvalue.RDFDatetime.FromSecondsSinceEpoch(0)