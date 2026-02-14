"""Service to handle robot map and position data."""
import json
from typing import Dict, Any, Optional
from datetime import datetime
import logging

_LOGGER = logging.getLogger(__name__)


class RobotMapService:
    """Manages robot map data and position tracking."""
    
    def __init__(self):
        """Initialize the map service."""
        self.current_position: Dict[str, float] = {"x": 0, "y": 0}
        self.map_data: Optional[Dict[str, Any]] = None
        self.update_timestamp: Optional[datetime] = None
    
    def update_robot_position(self, x: float, y: float) -> None:
        """Update current robot position.
        
        Args:
            x: X coordinate in map space
            y: Y coordinate in map space
        """
        self.current_position = {"x": float(x), "y": float(y)}
        self.update_timestamp = datetime.now()
        _LOGGER.debug(f"Robot position updated: {self.current_position}")
    
    def set_map_data(self, map_bytes: bytes) -> None:
        """Set the house map data.
        
        Args:
            map_bytes: Raw map image bytes (PNG format)
        """
        if map_bytes:
            import base64
            self.map_data = {
                "image": base64.b64encode(map_bytes).decode('utf-8'),
                "timestamp": datetime.now().isoformat()
            }
            _LOGGER.debug("Map data updated")
    
    def get_map_state(self) -> Dict[str, Any]:
        """Get the current map state including robot position.
        
        Returns:
            Dictionary with map and robot position data
        """
        return {
            "position": self.current_position,
            "has_map": self.map_data is not None,
            "timestamp": self.update_timestamp.isoformat() if self.update_timestamp else None
        }
    
    def get_map_image(self) -> Optional[str]:
        """Get base64 encoded map image.
        
        Returns:
            Base64 encoded image string or None
        """
        return self.map_data.get("image") if self.map_data else None
