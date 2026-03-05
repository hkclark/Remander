"""Command queueing and execution — bridges SAQ jobs with pydantic-graph workflows."""

import logging

from remander.models.command import Command
from remander.models.enums import CommandStatus
from remander.services.command import set_error_summary, transition_status
from remander.worker import get_queue

logger = logging.getLogger(__name__)


async def enqueue_command(command_id: int) -> None:
    """Transition a command to QUEUED and submit it to the SAQ job queue."""
    await transition_status(command_id, CommandStatus.QUEUED)
    queue = get_queue()
    if queue is not None:
        await queue.enqueue("process_command", command_id=command_id)


async def execute_command(command_id: int) -> None:
    """Execute a queued command by running its workflow graph.

    Handles lifecycle transitions: QUEUED -> RUNNING -> SUCCEEDED/FAILED/COMPLETED_WITH_ERRORS.
    Skips commands that have been cancelled before execution begins.
    """
    cmd = await Command.get(id=command_id)

    # Skip cancelled commands — they may have been cancelled while sitting in the queue
    if cmd.status == CommandStatus.CANCELLED:
        logger.info("Skipping cancelled command %d", command_id)
        return

    await transition_status(command_id, CommandStatus.RUNNING)

    try:
        result = await run_workflow(cmd)
        if result:
            # run_workflow returns True to indicate partial errors
            await transition_status(command_id, CommandStatus.COMPLETED_WITH_ERRORS)
        else:
            await transition_status(command_id, CommandStatus.SUCCEEDED)
    except Exception as e:
        logger.exception("Command %d failed: %s", command_id, e)
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
        host=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_username,
        password=settings.smtp_password.get_secret_value(),
        from_addr=settings.smtp_from,
        to_addr=settings.smtp_to,
        use_tls=settings.smtp_use_tls,
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

    state = WorkflowState(
        command_id=cmd.id,
        command_type=cmd.command_type,
        device_ids=device_ids,
        tag_filter=cmd.tag_filter,
        delay_minutes=cmd.delay_minutes,
        pause_minutes=cmd.pause_minutes,
    )

    graph, start_node = get_workflow_for_command(cmd.command_type)
    result = await graph.run(start_node, state=state, deps=deps)

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
        host=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_username,
        password=settings.smtp_password.get_secret_value(),
        from_addr=settings.smtp_from,
        to_addr=settings.smtp_to,
        use_tls=settings.smtp_use_tls,
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
