"""Workflow graph definitions — maps CommandType to pydantic-graph Graph."""

from __future__ import annotations

from pydantic_graph import BaseNode, Graph

from remander.models.enums import CommandType
from remander.workflows.nodes.bitmask import SetNotificationBitmasksNode, SetZoneMasksNode
from remander.workflows.nodes.delay import OptionalDelayNode
from remander.workflows.nodes.filter import FilterByTagNode
from remander.workflows.nodes.mute import IngressEgressMuteNode, WaitForMuteExpiryNode
from remander.workflows.nodes.notify import NotifyNode
from remander.workflows.nodes.nvr import NVRLoginNode, NVRLogoutNode
from remander.workflows.nodes.power import PowerOffNode, PowerOnNode, WaitForPowerOnNode
from remander.workflows.nodes.ptz import PTZCalibrateNode, SetPTZHomeNode, SetPTZPresetNode
from remander.workflows.nodes.save_restore import RestoreBitmasksNode, SaveBitmasksNode
from remander.workflows.nodes.schedule import ScheduleReArmNode
from remander.workflows.nodes.validate import ValidateNode

# Set Away workflow: Delay -> Login -> PowerOn -> Wait -> Calibrate ->
#   PTZPreset -> SetBitmasks -> SetZones -> Validate -> Logout -> Notify
# PowerOn/Wait come before Calibrate because the NVR returns no data for offline cameras.
# Bitmasks are NOT saved for AWAY — SaveBitmasks only serves PAUSE → rearm workflows
# (which reuse the same command_id for restore). HOME applies configured bitmasks directly.
set_away_graph = Graph(
    nodes=(
        OptionalDelayNode,
        NVRLoginNode,
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

# Set Home workflow: Login -> SetBitmasks(HOME) -> SetZones(HOME) ->
#   PTZHome -> PowerOff -> Validate -> Logout -> Notify
# RestoreBitmasks is not used here — HOME applies configured bitmasks directly.
# (RestoreBitmasks only works for PAUSE → rearm, which reuses the same command_id.)
set_home_graph = Graph(
    nodes=(
        NVRLoginNode,
        SetNotificationBitmasksNode,
        SetZoneMasksNode,
        SetPTZHomeNode,
        PowerOffNode,
        ValidateNode,
        NVRLogoutNode,
        NotifyNode,
    ),
    name="set_home",
)

# Set Away with Mute workflow: IngressEgressMute -> Delay -> Login -> PowerOn -> Wait ->
#   Calibrate -> PTZPreset -> WaitForMuteExpiry -> SetBitmasks -> SetZones -> Validate ->
#   Logout -> Notify
# IngressEgressMuteNode runs before the delay so cameras are silenced immediately on button press.
# WaitForMuteExpiryNode inserts between PTZPreset and SetBitmasks to hold until mute window closes.
set_away_with_mute_graph = Graph(
    nodes=(
        IngressEgressMuteNode,
        OptionalDelayNode,
        NVRLoginNode,
        PowerOnNode,
        WaitForPowerOnNode,
        PTZCalibrateNode,
        SetPTZPresetNode,
        WaitForMuteExpiryNode,
        SetNotificationBitmasksNode,
        SetZoneMasksNode,
        ValidateNode,
        NVRLogoutNode,
        NotifyNode,
    ),
    name="set_away_with_mute",
)

# Set Home with Mute workflow: IngressEgressMute -> Login -> PTZHome -> PowerOff ->
#   WaitForMuteExpiry -> SetBitmasks(HOME) -> SetZones(HOME) -> Validate -> Logout -> Notify
# PTZ/Power happen during the mute window; bitmasks are applied after mute expires.
set_home_with_mute_graph = Graph(
    nodes=(
        IngressEgressMuteNode,
        NVRLoginNode,
        SetPTZHomeNode,
        PowerOffNode,
        WaitForMuteExpiryNode,
        SetNotificationBitmasksNode,
        SetZoneMasksNode,
        ValidateNode,
        NVRLogoutNode,
        NotifyNode,
    ),
    name="set_home_with_mute",
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
    mute_enabled: bool = False,
) -> tuple[Graph, BaseNode]:
    """Return the graph and start node for a given command type.

    When mute_enabled=True, Away and Home commands use the mute graph variants
    that include IngressEgressMuteNode and WaitForMuteExpiryNode.
    """
    match command_type:
        case CommandType.SET_AWAY_NOW | CommandType.SET_AWAY_DELAYED:
            if mute_enabled:
                return set_away_with_mute_graph, IngressEgressMuteNode()
            return set_away_graph, OptionalDelayNode()
        case CommandType.SET_HOME_NOW:
            if mute_enabled:
                return set_home_with_mute_graph, IngressEgressMuteNode()
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
