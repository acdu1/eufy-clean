"""HTTP views for SVG streaming."""

from __future__ import annotations

import asyncio
import logging

from aiohttp import web
from homeassistant.components.http import HomeAssistantView

_LOGGER = logging.getLogger(__name__)


class RobovacSVGViewerView(HomeAssistantView):
    """Serve the SVG viewer HTML."""

    url = "/api/custom_component/robovac_mqtt/viewer"
    name = "robovac_svg_viewer"

    async def get(self, request: web.Request) -> web.Response:
        """Serve viewer HTML."""
        html = await self._get_viewer_html()
        return web.Response(text=html, content_type="text/html")

    @staticmethod
    async def _get_viewer_html() -> str:
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


class RobovacSVGStreamView(HomeAssistantView):
    """Serve the SVG stream via Server-Sent Events."""

    url = "/api/custom_component/robovac_mqtt/stream"
    name = "robovac_svg_stream"

    def __init__(self):
        """Initialize the stream view."""
        super().__init__()
        self.streaming_manager = None

    async def get(self, request: web.Request) -> web.StreamResponse:
        """Serve SVG stream."""
        if not self.streaming_manager:
            return web.Response(text="No streaming manager available", status=503)

        response = web.StreamResponse()
        response.content_type = "text/event-stream"
        response.headers["Cache-Control"] = "no-cache"
        response.headers["X-Accel-Buffering"] = "no"

        await response.prepare(request)

        try:
            async for message in self.streaming_manager.server.svg_stream_generator():
                await response.write(message.encode())
        except asyncio.CancelledError:
            pass
        except Exception as e:
            _LOGGER.error("Error streaming SVG: %s", e)

        return response
