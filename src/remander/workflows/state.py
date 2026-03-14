"""Workflow state and dependencies for pydantic-graph workflows."""

from dataclasses import dataclass, field
from datetime import datetime

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

    # Button-driven delay (seconds) — checked by OptionalDelayNode before delay_minutes
    delay_seconds: int | None = None

    # Per-device bitmask override built from button tag-rules: device_id -> hour_bitmask_id.
    # When non-empty, SetNotificationBitmasksNode applies the mapped bitmask per device
    # instead of the standard per-device lookup; devices absent from the map are skipped.
    override_bitmask_map: dict[int, int] = field(default_factory=dict)

    # Whether this is a re-arm workflow (triggered by timer, not a user command)
    is_rearm: bool = False

    # Tracks whether the NVR session is currently open. Set True by NVRLoginNode on success,
    # cleared by NVRLogoutNode. Used by run_workflow's finally block to force-logout if the
    # graph exits without reaching NVRLogoutNode (e.g. due to an unexpected exception).
    nvr_logged_in: bool = False

    # Validation discrepancies collected by ValidateNode
    validation_discrepancies: list[dict] = field(default_factory=list)

    # Final bitmask state per channel for notification display
    # channel -> {detection_type_str -> 24-char bitmask}
    channel_bitmask_results: dict[int, dict[str, str]] = field(default_factory=dict)

    # Ingress/egress notification mute settings
    mute_duration_seconds: int | None = None
    mute_tag_device_ids: list[int] = field(default_factory=list)
    mute_start_time: datetime | None = None


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
    timezone: str = "UTC"
    power_on_timeout_seconds: int = 120
    power_on_poll_interval_seconds: int = 10
    power_on_settle_seconds: int = 30
    ptz_settle_seconds: int = 10
