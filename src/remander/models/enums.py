"""Enum types for the Remander data model."""

from enum import StrEnum


class DeviceType(StrEnum):
    CAMERA = "camera"
    POWER = "power"


class DeviceBrand(StrEnum):
    REOLINK = "reolink"
    TAPO = "tapo"
    SONOFF = "sonoff"


class PowerDeviceSubtype(StrEnum):
    SMART_PLUG = "smart_plug"
    INLINE_SWITCH = "inline_switch"


class DetectionType(StrEnum):
    MOTION = "motion"
    PERSON = "person"
    VEHICLE = "vehicle"
    ANIMAL = "animal"
    FACE = "face"
    PACKAGE = "package"


class HourBitmaskSubtype(StrEnum):
    STATIC = "static"
    DYNAMIC = "dynamic"


class Mode(StrEnum):
    HOME = "home"
    AWAY = "away"


class CommandType(StrEnum):
    SET_AWAY_NOW = "set_away_now"
    SET_AWAY_DELAYED = "set_away_delayed"
    SET_HOME_NOW = "set_home_now"
    PAUSE_NOTIFICATIONS = "pause_notifications"
    PAUSE_RECORDING = "pause_recording"


class CommandStatus(StrEnum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    COMPLETED_WITH_ERRORS = "completed_with_errors"


class ActivityStatus(StrEnum):
    STARTED = "started"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"
