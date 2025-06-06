#!/usr/bin/env python
"""Implementation of a router class that does no ACL checks."""

from typing import Optional

from grr_response_proto.api import user_pb2 as api_user_pb2
from grr_response_server.gui import api_call_context
from grr_response_server.gui import api_call_router
from grr_response_server.gui.api_plugins import artifact as api_artifact
from grr_response_server.gui.api_plugins import client as api_client
from grr_response_server.gui.api_plugins import config as api_config
from grr_response_server.gui.api_plugins import cron as api_cron
from grr_response_server.gui.api_plugins import flow as api_flow
from grr_response_server.gui.api_plugins import hunt as api_hunt
from grr_response_server.gui.api_plugins import metadata as api_metadata
from grr_response_server.gui.api_plugins import osquery as api_osquery
from grr_response_server.gui.api_plugins import output_plugin as api_output_plugin
from grr_response_server.gui.api_plugins import reflection as api_reflection
from grr_response_server.gui.api_plugins import signed_commands as api_signed_commands
from grr_response_server.gui.api_plugins import stats as api_stats
from grr_response_server.gui.api_plugins import timeline as api_timeline
from grr_response_server.gui.api_plugins import user as api_user
from grr_response_server.gui.api_plugins import vfs as api_vfs
from grr_response_server.gui.api_plugins import yara as api_yara


class ApiCallRouterWithoutChecks(api_call_router.ApiCallRouterStub):
  """Router that does no ACL checks whatsoever."""

  # Artifacts methods.
  # =================
  #
  def ListArtifacts(self, args, context=None):
    return api_artifact.ApiListArtifactsHandler()

  def UploadArtifact(self, args, context=None):
    return api_artifact.ApiUploadArtifactHandler()

  def DeleteArtifacts(self, args, context=None):
    return api_artifact.ApiDeleteArtifactsHandler()

  # Clients methods.
  # ===============
  #
  def SearchClients(self, args, context=None):
    return api_client.ApiSearchClientsHandler()

  def VerifyAccess(self, args, context=None):
    return api_client.ApiVerifyAccessHandler()

  def GetClient(self, args, context=None):
    return api_client.ApiGetClientHandler()

  def GetClientVersions(self, args, context=None):
    return api_client.ApiGetClientVersionsHandler()

  def GetClientVersionTimes(self, args, context=None):
    return api_client.ApiGetClientVersionTimesHandler()

  def InterrogateClient(self, args, context=None):
    return api_client.ApiInterrogateClientHandler()

  def GetInterrogateOperationState(self, args, context=None):
    return api_client.ApiGetInterrogateOperationStateHandler()

  def GetLastClientIPAddress(self, args, context=None):
    return api_client.ApiGetLastClientIPAddressHandler()

  def ListClientCrashes(self, args, context=None):
    return api_client.ApiListClientCrashesHandler()

  def KillFleetspeak(
      self,
      args: api_client.ApiKillFleetspeakArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_client.ApiKillFleetspeakHandler:
    return api_client.ApiKillFleetspeakHandler()

  def RestartFleetspeakGrrService(
      self,
      args: api_client.ApiRestartFleetspeakGrrServiceArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_client.ApiRestartFleetspeakGrrServiceHandler:
    return api_client.ApiRestartFleetspeakGrrServiceHandler()

  def DeleteFleetspeakPendingMessages(
      self,
      args: api_client.ApiDeleteFleetspeakPendingMessagesArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_client.ApiDeleteFleetspeakPendingMessagesHandler:
    return api_client.ApiDeleteFleetspeakPendingMessagesHandler()

  def GetFleetspeakPendingMessages(
      self,
      args: api_client.ApiGetFleetspeakPendingMessagesArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_client.ApiGetFleetspeakPendingMessagesHandler:
    return api_client.ApiGetFleetspeakPendingMessagesHandler()

  def GetFleetspeakPendingMessageCount(
      self,
      args: api_client.ApiGetFleetspeakPendingMessageCountArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_client.ApiGetFleetspeakPendingMessageCountHandler:
    return api_client.ApiGetFleetspeakPendingMessageCountHandler()

  # Virtual file system methods.
  # ============================
  #
  def ListFiles(self, args, context=None):
    return api_vfs.ApiListFilesHandler()

  def BrowseFilesystem(
      self,
      args: api_vfs.ApiBrowseFilesystemArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_vfs.ApiBrowseFilesystemHandler:
    return api_vfs.ApiBrowseFilesystemHandler()

  def GetVfsFilesArchive(self, args, context=None):
    return api_vfs.ApiGetVfsFilesArchiveHandler()

  def GetFileDetails(self, args, context=None):
    return api_vfs.ApiGetFileDetailsHandler()

  def GetFileText(self, args, context=None):
    return api_vfs.ApiGetFileTextHandler()

  def GetFileBlob(self, args, context=None):
    return api_vfs.ApiGetFileBlobHandler()

  def GetFileVersionTimes(self, args, context=None):
    return api_vfs.ApiGetFileVersionTimesHandler()

  def GetFileDownloadCommand(self, args, context=None):
    return api_vfs.ApiGetFileDownloadCommandHandler()

  def CreateVfsRefreshOperation(self, args, context=None):
    return api_vfs.ApiCreateVfsRefreshOperationHandler()

  def GetVfsRefreshOperationState(self, args, context=None):
    return api_vfs.ApiGetVfsRefreshOperationStateHandler()

  def GetVfsTimeline(self, args, context=None):
    return api_vfs.ApiGetVfsTimelineHandler()

  def GetVfsTimelineAsCsv(self, args, context=None):
    return api_vfs.ApiGetVfsTimelineAsCsvHandler()

  def UpdateVfsFileContent(self, args, context=None):
    return api_vfs.ApiUpdateVfsFileContentHandler()

  def GetVfsFileContentUpdateState(self, args, context=None):
    return api_vfs.ApiGetVfsFileContentUpdateStateHandler()

  # Clients labels methods.
  # ======================
  #
  def ListClientsLabels(self, args, context=None):
    return api_client.ApiListClientsLabelsHandler()

  def AddClientsLabels(self, args, context=None):
    return api_client.ApiAddClientsLabelsHandler()

  def RemoveClientsLabels(self, args, context=None):
    return api_client.ApiRemoveClientsLabelsHandler()

  # Clients flows methods.
  # =====================
  #
  def ListFlows(self, args, context=None):
    return api_flow.ApiListFlowsHandler()

  def GetFlow(self, args, context=None):
    return api_flow.ApiGetFlowHandler()

  def CreateFlow(self, args, context=None):
    return api_flow.ApiCreateFlowHandler()

  def CancelFlow(self, args, context=None):
    return api_flow.ApiCancelFlowHandler()

  def ListFlowRequests(self, args, context=None):
    return api_flow.ApiListFlowRequestsHandler()

  def ListFlowResults(self, args, context=None):
    return api_flow.ApiListFlowResultsHandler()

  def GetExportedFlowResults(self, args, context=None):
    return api_flow.ApiGetExportedFlowResultsHandler()

  def GetFlowResultsExportCommand(self, args, context=None):
    return api_flow.ApiGetFlowResultsExportCommandHandler()

  def GetFlowFilesArchive(self, args, context=None):
    return api_flow.ApiGetFlowFilesArchiveHandler()

  def ListFlowOutputPlugins(self, args, context=None):
    return api_flow.ApiListFlowOutputPluginsHandler()

  def ListFlowOutputPluginLogs(self, args, context=None):
    return api_flow.ApiListFlowOutputPluginLogsHandler()

  def ListFlowOutputPluginErrors(self, args, context=None):
    return api_flow.ApiListFlowOutputPluginErrorsHandler()

  def ListFlowLogs(self, args, context=None):
    return api_flow.ApiListFlowLogsHandler()

  def GetCollectedTimeline(self, args, context=None):
    return api_timeline.ApiGetCollectedTimelineHandler()

  def UploadYaraSignature(
      self,
      args: api_yara.ApiUploadYaraSignatureArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_yara.ApiUploadYaraSignatureHandler:
    del args, context  # Unused.
    return api_yara.ApiUploadYaraSignatureHandler()

  def ExplainGlobExpression(
      self,
      args: api_flow.ApiExplainGlobExpressionArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_flow.ApiExplainGlobExpressionHandler:
    del args, context  # Unused.
    return api_flow.ApiExplainGlobExpressionHandler()

  def ScheduleFlow(
      self,
      args: api_flow.ApiCreateFlowArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_flow.ApiScheduleFlowHandler:
    return api_flow.ApiScheduleFlowHandler()

  def ListScheduledFlows(
      self,
      args: api_flow.ApiListScheduledFlowsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_flow.ApiListScheduledFlowsHandler:
    return api_flow.ApiListScheduledFlowsHandler()

  def UnscheduleFlow(
      self,
      args: api_flow.ApiUnscheduleFlowArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_flow.ApiUnscheduleFlowHandler:
    return api_flow.ApiUnscheduleFlowHandler()

  def GetOsqueryResults(
      self,
      args: api_osquery.ApiGetOsqueryResultsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    del args, context  # Unused.
    return api_osquery.ApiGetOsqueryResultsHandler()

  # Signed commands methods.
  # ========================
  #
  def ListSignedCommands(
      self,
      args: Optional[None] = None,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_signed_commands.ApiListSignedCommandsHandler:
    return api_signed_commands.ApiListSignedCommandsHandler()

  # Cron jobs methods.
  # =================
  #
  def ListCronJobs(self, args, context=None):
    return api_cron.ApiListCronJobsHandler()

  def CreateCronJob(self, args, context=None):
    return api_cron.ApiCreateCronJobHandler()

  def GetCronJob(self, args, context=None):
    return api_cron.ApiGetCronJobHandler()

  def ForceRunCronJob(self, args, context=None):
    return api_cron.ApiForceRunCronJobHandler()

  def ModifyCronJob(self, args, context=None):
    return api_cron.ApiModifyCronJobHandler()

  def ListCronJobRuns(self, args, context=None):
    return api_cron.ApiListCronJobRunsHandler()

  def GetCronJobRun(self, args, context=None):
    return api_cron.ApiGetCronJobRunHandler()

  def DeleteCronJob(self, args, context=None):
    return api_cron.ApiDeleteCronJobHandler()

  # Hunts methods.
  # =============
  #
  def ListHunts(self, args, context=None):
    return api_hunt.ApiListHuntsHandler()

  def VerifyHuntAccess(self, args, context=None):
    return api_hunt.ApiVerifyHuntAccessHandler()

  def GetHunt(self, args, context=None):
    return api_hunt.ApiGetHuntHandler()

  def ListHuntErrors(self, args, context=None):
    return api_hunt.ApiListHuntErrorsHandler()

  def ListHuntLogs(self, args, context=None):
    return api_hunt.ApiListHuntLogsHandler()

  def ListHuntResults(self, args, context=None):
    return api_hunt.ApiListHuntResultsHandler()

  def CountHuntResultsByType(self, args, context=None):
    return api_hunt.ApiCountHuntResultsByTypeHandler()

  def GetExportedHuntResults(self, args, context=None):
    return api_hunt.ApiGetExportedHuntResultsHandler()

  def GetHuntResultsExportCommand(self, args, context=None):
    return api_hunt.ApiGetHuntResultsExportCommandHandler()

  def ListHuntOutputPlugins(self, args, context=None):
    return api_hunt.ApiListHuntOutputPluginsHandler()

  def ListHuntOutputPluginLogs(self, args, context=None):
    return api_hunt.ApiListHuntOutputPluginLogsHandler()

  def ListHuntOutputPluginErrors(self, args, context=None):
    return api_hunt.ApiListHuntOutputPluginErrorsHandler()

  def ListHuntCrashes(self, args, context=None):
    return api_hunt.ApiListHuntCrashesHandler()

  def GetHuntClientCompletionStats(self, args, context=None):
    return api_hunt.ApiGetHuntClientCompletionStatsHandler()

  def GetHuntStats(self, args, context=None):
    return api_hunt.ApiGetHuntStatsHandler()

  def ListHuntClients(self, args, context=None):
    return api_hunt.ApiListHuntClientsHandler()

  def GetHuntContext(self, args, context=None):
    return api_hunt.ApiGetHuntContextHandler()

  def CreateHunt(self, args, context=None):
    return api_hunt.ApiCreateHuntHandler()

  def ModifyHunt(self, args, context=None):
    return api_hunt.ApiModifyHuntHandler()

  def DeleteHunt(self, args, context=None):
    return api_hunt.ApiDeleteHuntHandler()

  def GetHuntFilesArchive(self, args, context=None):
    return api_hunt.ApiGetHuntFilesArchiveHandler()

  def GetHuntFile(self, args, context=None):
    return api_hunt.ApiGetHuntFileHandler()

  def GetCollectedHuntTimelines(
      self,
      args: api_timeline.ApiGetCollectedHuntTimelinesArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_timeline.ApiGetCollectedHuntTimelinesHandler:
    return api_timeline.ApiGetCollectedHuntTimelinesHandler()

  # Stats metrics methods.
  # =====================
  #
  def ListReports(self, args, context=None):
    return api_stats.ApiListReportsHandler()

  def GetReport(self, args, context=None):
    return api_stats.ApiGetReportHandler()

  def IncrementCounterMetric(
      self,
      args: api_stats.ApiIncrementCounterMetricArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_stats.ApiIncrementCounterMetricHandler:
    return api_stats.ApiIncrementCounterMetricHandler()

  # Approvals methods.
  # =================
  #
  def CreateClientApproval(self, args, context=None):
    return api_user.ApiCreateClientApprovalHandler()

  def GetClientApproval(self, args, context=None):
    return api_user.ApiGetClientApprovalHandler()

  def GrantClientApproval(self, args, context=None):
    return api_user.ApiGrantClientApprovalHandler()

  def ListClientApprovals(self, args, context=None):
    return api_user.ApiListClientApprovalsHandler()

  def CreateHuntApproval(self, args, context=None):
    return api_user.ApiCreateHuntApprovalHandler()

  def GetHuntApproval(self, args, context=None):
    return api_user.ApiGetHuntApprovalHandler()

  def GrantHuntApproval(self, args, context=None):
    return api_user.ApiGrantHuntApprovalHandler()

  def ListHuntApprovals(self, args, context=None):
    return api_user.ApiListHuntApprovalsHandler()

  def CreateCronJobApproval(self, args, context=None):
    return api_user.ApiCreateCronJobApprovalHandler()

  def GetCronJobApproval(self, args, context=None):
    return api_user.ApiGetCronJobApprovalHandler()

  def GrantCronJobApproval(self, args, context=None):
    return api_user.ApiGrantCronJobApprovalHandler()

  def ListCronJobApprovals(self, args, context=None):
    return api_user.ApiListCronJobApprovalsHandler()

  def ListApproverSuggestions(self, args, context=None):
    return api_user.ApiListApproverSuggestionsHandler()

  # User settings methods.
  # =====================
  #
  def GetPendingUserNotificationsCount(self, args, context=None):
    return api_user.ApiGetPendingUserNotificationsCountHandler()

  def ListPendingUserNotifications(self, args, context=None):
    return api_user.ApiListPendingUserNotificationsHandler()

  def DeletePendingUserNotification(self, args, context=None):
    return api_user.ApiDeletePendingUserNotificationHandler()

  def ListAndResetUserNotifications(self, args, context=None):
    return api_user.ApiListAndResetUserNotificationsHandler()

  def GetGrrUser(self, args, context=None):
    interface_traits = api_user_pb2.ApiGrrUserInterfaceTraits(
        cron_jobs_nav_item_enabled=True,
        create_cron_job_action_enabled=True,
        hunt_manager_nav_item_enabled=True,
        create_hunt_action_enabled=True,
        show_statistics_nav_item_enabled=True,
        server_load_nav_item_enabled=True,
        manage_binaries_nav_item_enabled=True,
        upload_binary_action_enabled=True,
        settings_nav_item_enabled=True,
        artifact_manager_nav_item_enabled=True,
        upload_artifact_action_enabled=True,
        search_clients_action_enabled=True,
        browse_virtual_file_system_nav_item_enabled=True,
        start_client_flow_nav_item_enabled=True,
        manage_client_flows_nav_item_enabled=True,
        modify_client_labels_action_enabled=True,
        hunt_approval_required=False,
    )
    return api_user.ApiGetOwnGrrUserHandler(interface_traits=interface_traits)

  def UpdateGrrUser(self, args, context=None):
    return api_user.ApiUpdateGrrUserHandler()

  # Config methods.
  # ==============
  #
  def GetConfig(self, args, context=None):
    return api_config.ApiGetConfigHandler()

  def GetConfigOption(self, args, context=None):
    return api_config.ApiGetConfigOptionHandler()

  def ListGrrBinaries(self, args, context=None):
    return api_config.ApiListGrrBinariesHandler()

  def GetGrrBinary(self, args, context=None):
    return api_config.ApiGetGrrBinaryHandler()

  def GetGrrBinaryBlob(self, args, context=None):
    return api_config.ApiGetGrrBinaryBlobHandler()

  def GetUiConfig(self, args, context=None):
    return api_config.ApiGetUiConfigHandler()

  # Reflection methods.
  # ==================
  #
  def ListKbFields(self, args, context=None):
    return api_client.ApiListKbFieldsHandler()

  def ListFlowDescriptors(self, args, context=None):
    # TODO(user): move to reflection.py
    return api_flow.ApiListFlowDescriptorsHandler()

  def GetRDFValueDescriptor(self, args, context=None):
    return api_reflection.ApiGetRDFValueDescriptorHandler()

  def ListRDFValuesDescriptors(self, args, context=None):
    return api_reflection.ApiListRDFValuesDescriptorsHandler()

  def ListOutputPluginDescriptors(self, args, context=None):
    return api_output_plugin.ApiListOutputPluginDescriptorsHandler()

  def ListKnownEncodings(self, args, context=None):
    return api_vfs.ApiListKnownEncodingsHandler()

  def ListApiMethods(self, args, context=None):
    return api_reflection.ApiListApiMethodsHandler(self)

  def GetGrrVersion(
      self,
      args: None,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_metadata.ApiGetGrrVersionHandler:
    return api_metadata.ApiGetGrrVersionHandler()

  def GetOpenApiDescription(
      self,
      args: None,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_metadata.ApiGetOpenApiDescriptionHandler:
    return api_metadata.ApiGetOpenApiDescriptionHandler(self)
