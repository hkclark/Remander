"""Filter by tag workflow node."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from pydantic_graph import BaseNode, GraphRunContext

from remander.models.enums import ActivityStatus
from remander.services.activity import log_activity
from remander.services.tag import get_devices_by_tag
from remander.workflows.nodes.nvr import NVRLoginNode
from remander.workflows.state import WorkflowDeps, WorkflowState

logger = logging.getLogger(__name__)


@dataclass
class FilterByTagNode(BaseNode[WorkflowState, WorkflowDeps]):
    """Filter the device list to only those matching the command's tag filter."""

    async def run(self, ctx: GraphRunContext[WorkflowState, WorkflowDeps]) -> NVRLoginNode:
        logger.info(
            "[cmd %d] FilterByTag: tag_filter=%s", ctx.state.command_id, ctx.state.tag_filter
        )
        if not ctx.state.tag_filter:
            logger.info("[cmd %d] FilterByTag: skipped (no tag filter)", ctx.state.command_id)
            await log_activity(
                command_id=ctx.state.command_id,
                step_name="filter_by_tag",
                status=ActivityStatus.SKIPPED,
                detail="No tag filter",
            )
            return NVRLoginNode()

        tag_names = [t.strip() for t in ctx.state.tag_filter.split(",")]
        matching_ids: set[int] = set()
        for tag_name in tag_names:
            devices = await get_devices_by_tag(tag_name)
            logger.info(
                "[cmd %d] FilterByTag: tag '%s' matched %d device(s): %s",
                ctx.state.command_id,
                tag_name,
                len(devices),
                [d.name for d in devices],
            )
            matching_ids.update(d.id for d in devices)

        before_count = len(ctx.state.device_ids)
        ctx.state.device_ids = [did for did in ctx.state.device_ids if did in matching_ids]
        logger.info(
            "[cmd %d] FilterByTag: %d -> %d devices (tags: %s)",
            ctx.state.command_id,
            before_count,
            len(ctx.state.device_ids),
            ctx.state.tag_filter,
        )

        await log_activity(
            command_id=ctx.state.command_id,
            step_name="filter_by_tag",
            status=ActivityStatus.SUCCEEDED,
            detail=f"Filtered to {len(ctx.state.device_ids)} devices"
            f" by tags: {ctx.state.tag_filter}",
        )
        return NVRLoginNode()
