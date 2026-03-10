"""Workflow graph definitions — maps CommandType to pydantic-graph Graph."""

from __future__ import annotations

from pydantic_graph import BaseNode, Graph

from remander.models.enums import CommandType
from remander.workflows.nodes.bitmask import SetNotificationBitmasksNode, SetZoneMasksNode
from remander.workflows.nodes.delay import OptionalDelayNode
from remander.workflows.nodes.filter import FilterByTagNode
from remander.workflows.nodes.notify import NotifyNode
from remander.workflows.nodes.nvr import NVRLoginNode, NVRLogoutNode
from remander.workflows.nodes.power import PowerOffNode, PowerOnNode, WaitForPowerOnNode
from remander.workflows.nodes.ptz import PTZCalibrateNode, SetPTZHomeNode, SetPTZPresetNode
from remander.workflows.nodes.save_restore import RestoreBitmasksNode, SaveBitmasksNode
from remander.workflows.nodes.schedule import ScheduleReArmNode
from remander.workflows.nodes.validate import ValidateNode

# Set Away workflow: Delay -> Login -> Save -> PowerOn -> Wait -> Calibrate ->
#   PTZPreset -> SetBitmasks -> SetZones -> Validate -> Logout -> Notify
set_away_graph = Graph(
    nodes=(
        OptionalDelayNode,
        NVRLoginNode,
        SaveBitmasksNode,
        PowerOnNode,
        WaitForPowerOnNode,
        PTZCalibrateNode,
        SetPTZPresetNode,
        SetNotificationBitmasksNode,
        SetZoneMasksNode,
        ValidateNode,
        NVRLogoutNode,
        NotifyNode,
    ),
    name="set_away",
)

# Set Home workflow: Login -> Restore -> PTZHome -> PowerOff -> Validate -> Logout -> Notify
set_home_graph = Graph(
    nodes=(
        NVRLoginNode,
        RestoreBitmasksNode,
        SetPTZHomeNode,
        PowerOffNode,
        ValidateNode,
        NVRLogoutNode,
        NotifyNode,
    ),
    name="set_home",
)

# Pause Notifications workflow: Filter -> Login -> Save -> SetBitmasks -> SetZones ->
#   Logout -> ScheduleReArm
pause_notifications_graph = Graph(
    nodes=(
        FilterByTagNode,
        NVRLoginNode,
        SaveBitmasksNode,
        PowerOnNode,
        WaitForPowerOnNode,
        PTZCalibrateNode,
        SetPTZPresetNode,
        SetNotificationBitmasksNode,
        SetZoneMasksNode,
        ValidateNode,
        NVRLogoutNode,
        ScheduleReArmNode,
        NotifyNode,
    ),
    name="pause_notifications",
)

# Pause Recording workflow: same structure as pause notifications
pause_recording_graph = Graph(
    nodes=(
        FilterByTagNode,
        NVRLoginNode,
        SaveBitmasksNode,
        PowerOnNode,
        WaitForPowerOnNode,
        PTZCalibrateNode,
        SetPTZPresetNode,
        SetNotificationBitmasksNode,
        SetZoneMasksNode,
        ValidateNode,
        NVRLogoutNode,
        ScheduleReArmNode,
        NotifyNode,
    ),
    name="pause_recording",
)

# Apply Bitmask workflow (OTHER button type): Login -> SetBitmasks -> Validate -> Logout -> Notify
# No power control, PTZ, zone masks, or mode change.
apply_bitmask_graph = Graph(
    nodes=(
        NVRLoginNode,
        SetNotificationBitmasksNode,
        ValidateNode,
        NVRLogoutNode,
        NotifyNode,
    ),
    name="apply_bitmask",
)

# Re-Arm workflow: Login -> Restore -> PTZHome -> PowerOff -> Validate -> Logout -> Notify
rearm_graph = Graph(
    nodes=(
        NVRLoginNode,
        RestoreBitmasksNode,
        SetPTZHomeNode,
        PowerOffNode,
        ValidateNode,
        NVRLogoutNode,
        NotifyNode,
    ),
    name="rearm",
)


def get_workflow_for_command(
    command_type: CommandType | str,
) -> tuple[Graph, BaseNode]:
    """Return the graph and start node for a given command type."""
    match command_type:
        case CommandType.SET_AWAY_NOW:
            return set_away_graph, OptionalDelayNode()
        case CommandType.SET_AWAY_DELAYED:
            return set_away_graph, OptionalDelayNode()
        case CommandType.SET_HOME_NOW:
            return set_home_graph, NVRLoginNode()
        case CommandType.PAUSE_NOTIFICATIONS:
            return pause_notifications_graph, FilterByTagNode()
        case CommandType.PAUSE_RECORDING:
            return pause_recording_graph, FilterByTagNode()
        case CommandType.APPLY_BITMASK:
            return apply_bitmask_graph, NVRLoginNode()
        case "rearm":
            return rearm_graph, NVRLoginNode()
        case _:
            raise ValueError(f"Unknown command type: {command_type}")
