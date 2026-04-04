"""Lightweight SVG stream server for Home Assistant Green.

Pure async SVG streaming with minimal memory footprint.
No heavy dependencies (PIL, cairosvg, av). Just raw SVG updates via HTTP.
"""

# pylint: disable=no-self-use

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from datetime import datetime
from typing import Any

_LOGGER = logging.getLogger(__name__)


@dataclass
class SVGStreamConfig:
    """Configuration for SVG stream."""

    enabled: bool = True
    update_interval: float = 2.0  # Update every 2 seconds


class EnhancedSVGGenerator:
    """Generate enhanced SVG with minimal overhead."""

    @staticmethod
    def generate(
        rooms: list[dict[str, Any]],
        current_room: str,
        confidence: float,
        robot_x: int = 0,
        robot_y: int = 0,
        position_history: list[tuple[int, int]] | None = None,
        timestamp: str | None = None,
    ) -> str:
        """Generate enhanced SVG with animations and visual effects.

        Lightweight implementation for HA Green - no external rendering.
        """
        if not rooms:
            return ""

        if position_history is None:
            position_history = []

        if timestamp is None:
            timestamp = datetime.now().strftime("%H:%M:%S")

        # Calculate grid layout
        num_rooms = len(rooms)
        cols = min(3, max(1, int(num_rooms**0.5)))
        rows = (num_rooms + cols - 1) // cols

        room_width = 140
        room_height = 100
        padding = 15
        margin = 20
        header_height = 50

        svg_width = cols * (room_width + padding) + padding + margin * 2
        svg_height = (
            rows * (room_height + padding) + padding + header_height + margin * 2
        )

        # Build SVG
        svg = [
            f'<svg width="{svg_width}" height="{svg_height}" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {svg_width} {svg_height}">',
            "<defs><style>",
            ".room{fill:#e8f4f8;stroke:#0077be;stroke-width:2}",
            ".room.active{fill:#fef3c7;stroke:#f59e0b;stroke-width:3}",
            ".room-label{font-family:sans-serif;font-size:14px;font-weight:600;text-anchor:middle;fill:#0077be}",
            ".room-label.active{fill:#d97706}",
            ".header-text{font-family:sans-serif;font-size:16px;font-weight:600;fill:#1f2937}",
            ".timestamp{font-family:monospace;font-size:12px;fill:#6b7280}",
            ".robot{fill:#ef4444;stroke:#fff;stroke-width:2}",
            ".trail{fill:none;stroke:#60a5fa;stroke-width:1.5;opacity:0.4}",
            ".status-bar{fill:#f0f9ff;stroke:#0284c7;stroke-width:1}",
            ".conf-bg{fill:#e5e7eb}",
            ".conf-fill{fill:#10b981}",
            ".conf-low{fill:#ef4444}.conf-med{fill:#f59e0b}.conf-high{fill:#10b981}",
            ".conf-text{font-family:sans-serif;font-size:11px;text-anchor:middle;fill:#4b5563;font-weight:500}",
            "</style></defs>",
        ]

        # Header
        svg.append(
            f'<rect x="{margin}" y="{margin}" width="{svg_width - margin*2}" height="{header_height}" class="status-bar" rx="6"/>'
        )
        svg.append(
            f'<text x="{margin + 12}" y="{margin + 30}" class="header-text">Robot Position Map</text>'
        )
        svg.append(
            f'<text x="{svg_width - margin - 12}" y="{margin + 30}" text-anchor="end" class="timestamp">{timestamp}</text>'
        )

        # Confidence bar
        conf_bar_width = 120
        conf_bar_height = 6
        conf_bar_x = margin + 12
        conf_bar_y = margin + header_height - 14

        svg.append(
            f'<rect x="{conf_bar_x}" y="{conf_bar_y}" width="{conf_bar_width}" height="{conf_bar_height}" class="conf-bg" rx="3"/>'
        )

        # Confidence fill
        if confidence > 0.8:
            conf_color = "conf-high"
        elif confidence > 0.5:
            conf_color = "conf-med"
        else:
            conf_color = "conf-low"

        conf_fill_width = conf_bar_width * confidence
        svg.append(
            f'<rect x="{conf_bar_x}" y="{conf_bar_y}" width="{conf_fill_width}" height="{conf_bar_height}" class="{conf_color}" rx="3"/>'
        )
        svg.append(
            f'<text x="{conf_bar_x + conf_bar_width + 8}" y="{conf_bar_y + 10}" class="conf-text">Confidence: {int(confidence * 100)}%</text>'
        )

        # Rooms start position
        rooms_start_y = margin + header_height + 15

        # Draw position history trail
        if position_history and len(position_history) > 1:
            trail_points = " ".join(
                [f"{x},{y}" for x, y in position_history[-10:]]
            )  # Last 10 points
            svg.append(f'<polyline points="{trail_points}" class="trail"/>')

        # Draw rooms
        for i, room in enumerate(rooms):
            row = i // cols
            col = i % cols

            x = margin + col * (room_width + padding) + padding
            y = rooms_start_y + row * (room_height + padding) + padding

            room_name = room.get("name", f"Room {room.get('id', i + 1)}")
            is_current = room_name == current_room

            # Room rectangle
            room_class = "room active" if is_current else "room"
            svg.append(
                f'<rect x="{x}" y="{y}" width="{room_width}" height="{room_height}" class="{room_class}" rx="8"/>'
            )

            # Room label
            text_x = x + room_width / 2
            text_y = y + room_height / 2 + 5
            label_class = "room-label active" if is_current else "room-label"
            svg.append(
                f'<text x="{text_x}" y="{text_y}" class="{label_class}">{room_name}</text>'
            )

            # Robot indicator
            if is_current and confidence > 0:
                robot_cx = x + room_width / 2
                robot_cy = y + room_height / 2 - 15
                svg.append(
                    f'<circle cx="{robot_cx}" cy="{robot_cy}" r="8" class="robot"/>'
                )

        svg.append("</svg>")
        return "".join(svg)


class SVGStreamServer:
    """Lightweight HTTP-based SVG stream server for HA Green."""

    def __init__(self, config: SVGStreamConfig | None = None):
        """Initialize SVG stream server."""
        self.config = config or SVGStreamConfig()
        self._current_svg: str = ""
        self._update_event = asyncio.Event()
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        """Start the stream server."""
        if self.config.enabled:
            _LOGGER.debug("SVG stream server initialized")

    async def stop(self) -> None:
        """Stop the stream server."""
        _LOGGER.debug("SVG stream server stopped")

    async def update_svg(self, svg_content: str) -> None:
        """Update the current SVG content."""
        async with self._lock:
            if self._current_svg != svg_content:
                self._current_svg = svg_content
                self._update_event.set()

    async def get_current_svg(self) -> str:
        """Get the current SVG content."""
        async with self._lock:
            return self._current_svg

    async def svg_stream_generator(self) -> AsyncGenerator[str]:
        """Generate SVG stream updates via Server-Sent Events.

        Lightweight streaming format suitable for HA Green.
        """
        while self.config.enabled:
            try:
                svg = await self.get_current_svg()

                if svg:
                    # Server-Sent Events format
                    timestamp = datetime.now().isoformat()
                    yield f"event: svg_update\ndata: {timestamp}\n\n"
                    yield f"data: {svg}\n\n"

                # Wait for update or timeout
                try:
                    await asyncio.wait_for(
                        self._update_event.wait(),
                        timeout=self.config.update_interval,
                    )
                    self._update_event.clear()
                except TimeoutError:
                    pass

            except asyncio.CancelledError:
                break
            except Exception as e:
                _LOGGER.error("Error in SVG stream: %s", e)
                await asyncio.sleep(self.config.update_interval)

    @staticmethod
    async def get_viewer_html() -> str:
        """Get minimal HTML5 viewer for SVG streaming."""
        return """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Robot Position</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { background: #1a1a1a; color: #fff; font-family: system-ui; }
        .container { max-width: 800px; margin: 20px auto; }
        .status { font-size: 12px; color: #888; text-align: center; margin-top: 10px; }
        svg { width: 100%; height: auto; background: white; border: 1px solid #333; }
    </style>
</head>
<body>
    <div class="container">
        <div id="viewer"></div>
        <div class="status" id="status">Loading...</div>
    </div>
    <script>
        const viewer = document.getElementById('viewer');
        const status = document.getElementById('status');
        let buffer = '';

        function connect() {
            const es = new EventSource('./stream');
            es.addEventListener('svg_update', (e) => {
                status.textContent = 'Connected • ' + new Date().toLocaleTimeString();
            });
            es.addEventListener('message', (e) => {
                if (e.data.includes('<svg')) {
                    const start = e.data.indexOf('<svg');
                    const end = e.data.indexOf('</svg>') + 6;
                    if (start !== -1 && end > start) {
                        viewer.innerHTML = e.data.substring(start, end);
                    }
                }
            });
            es.onerror = () => {
                status.textContent = 'Reconnecting...';
                es.close();
                setTimeout(connect, 3000);
            };
        }
        connect();
    </script>
</body>
</html>"""
