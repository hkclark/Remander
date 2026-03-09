"""Workflow state and dependencies for pydantic-graph workflows."""

from dataclasses import dataclass, field

from remander.clients.reolink import ReolinkNVRClient
from remander.clients.sonoff import SonoffClient
from remander.clients.tapo import TapoClient
from remander.models.enums import CommandType
from remander.services.notification import NotificationSender


# Reason: dataclass required by pydantic-graph for state (must be mutable)
@dataclass
class WorkflowState:
    """Shared mutable state passed through all workflow nodes."""

    command_id: int
    command_type: CommandType
    device_ids: list[int]

    # Per-device results: device_id -> "succeeded" | "failed" | "skipped"
    device_results: dict[int, str] = field(default_factory=dict)

    # Whether any device encountered errors during the workflow
    has_errors: bool = False

    # Expected bitmask values for post-command validation
    # device_id -> {detection_type -> {hour_bitmask, zone_mask}}
    expected_bitmasks: dict[int, dict] = field(default_factory=dict)

    # Tag filter for pause commands
    tag_filter: str | None = None

    # Delay/pause settings
    delay_minutes: int | None = None
    pause_minutes: int | None = None

    # Whether this is a re-arm workflow (triggered by timer, not a user command)
    is_rearm: bool = False

    # Validation discrepancies collected by ValidateNode
    validation_discrepancies: list[dict] = field(default_factory=list)

    # Final bitmask state per channel for notification display
    # channel -> {detection_type_str -> 24-char bitmask}
    channel_bitmask_results: dict[int, dict[str, str]] = field(default_factory=dict)


# Reason: dataclass required by pydantic-graph for deps (immutable by convention)
@dataclass
class WorkflowDeps:
    """Immutable dependencies injected at workflow run time."""

    nvr_client: ReolinkNVRClient
    tapo_client: TapoClient
    sonoff_client: SonoffClient
    notification_sender: NotificationSender
    latitude: float = 0.0
    longitude: float = 0.0
