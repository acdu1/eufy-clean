"""Lightweight streaming integration for coordinator."""

# pylint: disable=no-self-use

from __future__ import annotations

import logging
from typing import Any

from .svg_stream import EnhancedSVGGenerator, SVGStreamConfig, SVGStreamServer

_LOGGER = logging.getLogger(__name__)


class StreamingManager:
    """Manages SVG streaming with minimal resource usage."""

    def __init__(self, device_name: str):
        """Initialize streaming manager."""
        self.device_name = device_name
        self.config = SVGStreamConfig(enabled=True)
        self.server = SVGStreamServer(self.config)
        self._position_history: list[tuple[int, int]] = []
        self._max_history = 20  # Keep only last 20 positions

    async def start(self) -> None:
        """Start streaming."""
        await self.server.start()
        _LOGGER.debug("Streaming manager started for %s", self.device_name)

    async def stop(self) -> None:
        """Stop streaming."""
        await self.server.stop()
        _LOGGER.debug("Streaming manager stopped")

    async def update_position(
        self,
        rooms: list[dict[str, Any]],
        current_room: str,
        confidence: float,
        robot_x: int = 0,
        robot_y: int = 0,
    ) -> None:
        """Update robot position and generate SVG.

        Called periodically (every 2 seconds) from coordinator.
        """
        # Track position history
        if robot_x > 0 or robot_y > 0:
            self._position_history.append((robot_x, robot_y))
            if len(self._position_history) > self._max_history:
                self._position_history.pop(0)

        # Generate SVG
        svg = EnhancedSVGGenerator.generate(
            rooms=rooms,
            current_room=current_room,
            confidence=confidence,
            robot_x=robot_x,
            robot_y=robot_y,
            position_history=self._position_history,
        )

        # Update stream
        await self.server.update_svg(svg)

    async def get_current_svg(self) -> str:
        """Get current SVG for sensor."""
        return await self.server.get_current_svg()

    async def get_viewer_html(self) -> str:
        """Get HTML viewer."""
        return await SVGStreamServer.get_viewer_html()
