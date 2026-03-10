"""Command queueing and execution — bridges SAQ jobs with pydantic-graph workflows."""

import asyncio
import logging

from remander.models.command import Command
from remander.models.enums import CommandStatus
from remander.services.command import set_error_summary, transition_status
from remander.worker import get_queue

logger = logging.getLogger(__name__)


async def enqueue_command(command_id: int) -> None:
    """Transition a command to QUEUED and submit it to the SAQ job queue."""
    from remander.config import get_settings

    logger.info("[cmd %d] Enqueuing command to SAQ job queue", command_id)
    await transition_status(command_id, CommandStatus.QUEUED)
    queue = get_queue()
    if queue is not None:
        timeout = get_settings().job_timeout_seconds
        await queue.enqueue("process_command", command_id=command_id, timeout=timeout)
        logger.info("[cmd %d] Command enqueued successfully", command_id)


async def execute_command(command_id: int) -> None:
    """Execute a queued command by running its workflow graph.

    Handles lifecycle transitions: QUEUED -> RUNNING -> SUCCEEDED/FAILED/COMPLETED_WITH_ERRORS.
    Skips commands that have been cancelled before execution begins.
    """
    cmd = await Command.get(id=command_id)

    # Skip cancelled commands — they may have been cancelled while sitting in the queue
    if cmd.status == CommandStatus.CANCELLED:
        logger.info("[cmd %d] Skipping cancelled command", command_id)
        return

    logger.info(
        "[cmd %d] Executing command: type=%s tag_filter=%s delay=%s pause=%s",
        command_id,
        cmd.command_type,
        cmd.tag_filter,
        cmd.delay_minutes,
        cmd.pause_minutes,
    )
    await transition_status(command_id, CommandStatus.RUNNING)

    try:
        result = await run_workflow(cmd)
        if result:
            # run_workflow returns True to indicate partial errors
            logger.warning("[cmd %d] Command completed with errors", command_id)
            await transition_status(command_id, CommandStatus.COMPLETED_WITH_ERRORS)
        else:
            logger.info("[cmd %d] Command succeeded", command_id)
            await transition_status(command_id, CommandStatus.SUCCEEDED)
    except asyncio.CancelledError:
        # SAQ job was cancelled or timed out — CancelledError is BaseException, not Exception
        logger.warning("[cmd %d] Command job was cancelled or timed out", command_id)
        await transition_status(command_id, CommandStatus.FAILED)
        await set_error_summary(command_id, "Job timed out or was cancelled")
        raise  # re-raise so SAQ knows the job did not complete
    except Exception as e:
        logger.exception("[cmd %d] Command failed: %s", command_id, e)
        await transition_status(command_id, CommandStatus.FAILED)
        await set_error_summary(command_id, str(e))


async def run_workflow(cmd: Command) -> bool | None:
    """Instantiate and run the pydantic-graph workflow for a command.

    Returns None on success, True if the workflow completed with partial errors.
    Raises on total failure.
    """
    # Build deps from application config and clients
    from remander.clients.email import EmailNotificationSender
    from remander.clients.reolink import ReolinkNVRClient
    from remander.clients.sonoff import SonoffClient
    from remander.clients.tapo import TapoClient
    from remander.config import get_settings
    from remander.models.device import Device
    from remander.workflows.graphs import get_workflow_for_command
    from remander.workflows.state import WorkflowDeps, WorkflowState

    settings = get_settings()

    nvr_client = ReolinkNVRClient(
        host=settings.nvr_host,
        port=settings.nvr_port,
        username=settings.nvr_username,
        password=settings.nvr_password.get_secret_value(),
        use_https=settings.nvr_use_https,
    )
    tapo_client = TapoClient()
    sonoff_client = SonoffClient()
    notification_sender = EmailNotificationSender(
        smtp_host=settings.smtp_host,
        smtp_port=settings.smtp_port,
        smtp_username=settings.smtp_username,
        smtp_password=settings.smtp_password.get_secret_value(),
        smtp_from=settings.smtp_from,
        smtp_to=settings.smtp_to,
        smtp_use_tls=settings.smtp_use_tls,
    )

    # Gather enabled device IDs
    devices = await Device.filter(is_enabled=True)
    device_ids = [d.id for d in devices]

    deps = WorkflowDeps(
        nvr_client=nvr_client,
        tapo_client=tapo_client,
        sonoff_client=sonoff_client,
        notification_sender=notification_sender,
        latitude=settings.latitude,
        longitude=settings.longitude,
    )

    # Build per-device bitmask map when command was triggered by a dashboard button.
    # Each rule maps tag -> hour_bitmask; we expand to device_id -> hour_bitmask_id
    # so the workflow node can look up the right bitmask per device without querying tags.
    override_bitmask_map: dict[int, int] = {}
    delay_seconds: int | None = cmd.delay_seconds
    if cmd.dashboard_button_id is not None:
        from remander.models.dashboard_button_bitmask_rule import DashboardButtonBitmaskRule

        rules = await DashboardButtonBitmaskRule.filter(
            dashboard_button_id=cmd.dashboard_button_id
        ).prefetch_related("tag")
        enabled_device_ids = set(device_ids)
        for rule in rules:
            tag_devices = await rule.tag.devices.filter(is_enabled=True)
            for device in tag_devices:
                if device.id in enabled_device_ids:
                    override_bitmask_map[device.id] = rule.hour_bitmask_id

    state = WorkflowState(
        command_id=cmd.id,
        command_type=cmd.command_type,
        device_ids=device_ids,
        tag_filter=cmd.tag_filter,
        delay_minutes=cmd.delay_minutes,
        delay_seconds=delay_seconds,
        pause_minutes=cmd.pause_minutes,
        override_bitmask_map=override_bitmask_map,
    )

    graph, start_node = get_workflow_for_command(cmd.command_type)
    logger.info(
        "[cmd %d] Starting workflow: graph=%s start_node=%s devices=%s",
        cmd.id,
        type(graph).__name__,
        type(start_node).__name__,
        device_ids,
    )
    result = await graph.run(start_node, state=state, deps=deps)
    logger.info("[cmd %d] Workflow finished: has_errors=%s", cmd.id, result.state.has_errors)

    return True if result.state.has_errors else None


async def execute_rearm(command_id: int) -> None:
    """Run the re-arm workflow to restore bitmasks saved by a pause command.

    Creates a re-arm state from the original pause command's context and
    runs the rearm workflow graph.
    """
    from remander.clients.email import EmailNotificationSender
    from remander.clients.reolink import ReolinkNVRClient
    from remander.clients.sonoff import SonoffClient
    from remander.clients.tapo import TapoClient
    from remander.config import get_settings
    from remander.models.device import Device
    from remander.workflows.graphs import get_workflow_for_command
    from remander.workflows.state import WorkflowDeps, WorkflowState

    logger.info("[cmd %d] Starting re-arm workflow", command_id)
    cmd = await Command.get(id=command_id)
    settings = get_settings()

    nvr_client = ReolinkNVRClient(
        host=settings.nvr_host,
        port=settings.nvr_port,
        username=settings.nvr_username,
        password=settings.nvr_password.get_secret_value(),
        use_https=settings.nvr_use_https,
    )
    tapo_client = TapoClient()
    sonoff_client = SonoffClient()
    notification_sender = EmailNotificationSender(
        smtp_host=settings.smtp_host,
        smtp_port=settings.smtp_port,
        smtp_username=settings.smtp_username,
        smtp_password=settings.smtp_password.get_secret_value(),
        smtp_from=settings.smtp_from,
        smtp_to=settings.smtp_to,
        smtp_use_tls=settings.smtp_use_tls,
    )

    devices = await Device.filter(is_enabled=True)
    device_ids = [d.id for d in devices]

    deps = WorkflowDeps(
        nvr_client=nvr_client,
        tapo_client=tapo_client,
        sonoff_client=sonoff_client,
        notification_sender=notification_sender,
        latitude=settings.latitude,
        longitude=settings.longitude,
    )

    state = WorkflowState(
        command_id=cmd.id,
        command_type=cmd.command_type,
        device_ids=device_ids,
        is_rearm=True,
    )

    graph, start_node = get_workflow_for_command("rearm")

    try:
        await graph.run(start_node, state=state, deps=deps)
        logger.info("Re-arm completed for command %d", command_id)
    except Exception:
        logger.exception("Re-arm failed for command %d", command_id)
