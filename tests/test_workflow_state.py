"""Tests for the workflow state and deps — RED phase (TDD)."""

from unittest.mock import AsyncMock

from remander.models.enums import CommandType
from remander.workflows.state import WorkflowDeps, WorkflowState
from tests.factories import create_camera, create_command


class TestWorkflowState:
    async def test_creation_with_command(self) -> None:
        cmd = await create_command(command_type=CommandType.SET_AWAY_NOW)
        camera = await create_camera(name="WF Cam")

        state = WorkflowState(
            command_id=cmd.id,
            command_type=cmd.command_type,
            device_ids=[camera.id],
        )
        assert state.command_id == cmd.id
        assert state.command_type == CommandType.SET_AWAY_NOW
        assert state.device_ids == [camera.id]

    async def test_tracks_per_device_results(self) -> None:
        state = WorkflowState(
            command_id=1,
            command_type=CommandType.SET_AWAY_NOW,
            device_ids=[1, 2, 3],
        )
        state.device_results[1] = "succeeded"
        state.device_results[2] = "failed"
        assert state.device_results[1] == "succeeded"
        assert state.device_results[2] == "failed"
        assert 3 not in state.device_results

    async def test_has_errors_tracking(self) -> None:
        state = WorkflowState(
            command_id=1,
            command_type=CommandType.SET_AWAY_NOW,
            device_ids=[],
        )
        assert state.has_errors is False
        state.has_errors = True
        assert state.has_errors is True

    async def test_expected_bitmasks_storage(self) -> None:
        """WorkflowState should track expected bitmask values for validation."""
        state = WorkflowState(
            command_id=1,
            command_type=CommandType.SET_AWAY_NOW,
            device_ids=[1],
        )
        state.expected_bitmasks[1] = {"motion": {"hour_bitmask": "1" * 24, "zone_mask": "1" * 4800}}
        assert "motion" in state.expected_bitmasks[1]


class TestWorkflowDeps:
    def test_creation(self) -> None:
        nvr = AsyncMock()
        tapo = AsyncMock()
        sonoff = AsyncMock()
        notifier = AsyncMock()

        deps = WorkflowDeps(
            nvr_client=nvr,
            tapo_client=tapo,
            sonoff_client=sonoff,
            notification_sender=notifier,
            latitude=40.7128,
            longitude=-74.0060,
        )
        assert deps.nvr_client is nvr
        assert deps.tapo_client is tapo
        assert deps.sonoff_client is sonoff
        assert deps.notification_sender is notifier
        assert deps.latitude == 40.7128
