/**
 * Eufy Robot Map Viewer
 * Displays real-time robot position on house map
 */

class RobotMapViewer {
    constructor() {
        this.canvas = document.getElementById('map-canvas');
        this.ctx = this.canvas.getContext('2d');
        this.mapImage = null;
        this.robotPosition = { x: 0, y: 0 };
        this.scale = 1;
        this.pan = { x: 0, y: 0 };
        this.isLoading = true;
        
        this.setupCanvas();
        this.setupEventListeners();
        this.initializeWebSocket();
    }
    
    setupCanvas() {
        const rect = this.canvas.parentElement.getBoundingClientRect();
        this.canvas.width = rect.width;
        this.canvas.height = rect.height;
    }
    
    setupEventListeners() {
        window.addEventListener('resize', () => this.setupCanvas());
        this.canvas.addEventListener('wheel', (e) => this.handleZoom(e));
        this.canvas.addEventListener('mousemove', (e) => this.handlePan(e));
        this.canvas.addEventListener('click', (e) => this.handleClick(e));
    }
    
    initializeWebSocket() {
        // Connect to Home Assistant WebSocket API or REST endpoint
        this.pollMapData();
    }
    
    async pollMapData() {
        try {
            const response = await fetch('/api/states/vacuum.eufy_clean');
            if (response.ok) {
                const state = await response.json();
                this.updateFromState(state);
            }
        } catch (error) {
            console.error('Failed to fetch map data:', error);
            this.showError('Failed to load map data');
        }
        
        // Poll every 500ms for real-time updates
        setTimeout(() => this.pollMapData(), 500);
    }
    
    updateFromState(state) {
        if (state.attributes) {
            // Update robot position
            if (state.attributes.position) {
                const pos = state.attributes.position;
                this.robotPosition = {
                    x: pos.x || 0,
                    y: pos.y || 0
                };
            }
            
            // Update map image
            if (state.attributes.map_url) {
                this.loadMapImage(state.attributes.map_url);
            }
            
            // Update status display
            this.updateStatusDisplay(state);
        }
        
        this.isLoading = false;
        this.render();
    }
    
    loadMapImage(url) {
        const img = new Image();
        img.crossOrigin = 'anonymous';
        img.onload = () => {
            this.mapImage = img;
            this.setupCanvas(); // Adjust canvas size based on image
            this.render();
        };
        img.onerror = () => {
            this.showError('Failed to load map image');
        };
        img.src = url;
    }
    
    handleZoom(event) {
        event.preventDefault();
        const zoomFactor = event.deltaY > 0 ? 0.9 : 1.1;
        const oldScale = this.scale;
        this.scale *= zoomFactor;
        this.scale = Math.max(0.5, Math.min(3, this.scale)); // Clamp between 0.5 and 3
        
        // Zoom towards mouse position
        const rect = this.canvas.getBoundingClientRect();
        const mouseX = event.clientX - rect.left;
        const mouseY = event.clientY - rect.top;
        
        this.pan.x = mouseX - (mouseX - this.pan.x) * (this.scale / oldScale);
        this.pan.y = mouseY - (mouseY - this.pan.y) * (this.scale / oldScale);
        
        this.render();
    }
    
    handlePan(event) {
        if (event.buttons !== 1) return; // Only pan on mouse drag
        this.pan.x += event.movementX;
        this.pan.y += event.movementY;
        this.render();
    }
    
    handleClick(event) {
        // Click to center on robot
        const rect = this.canvas.getBoundingClientRect();
        this.pan.x = this.canvas.width / 2 - this.robotPosition.x * this.scale;
        this.pan.y = this.canvas.height / 2 - this.robotPosition.y * this.scale;
        this.render();
    }
    
    render() {
        // Clear canvas
        this.ctx.fillStyle = '#f5f5f5';
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
        
        this.ctx.save();
        this.ctx.translate(this.pan.x, this.pan.y);
        this.ctx.scale(this.scale, this.scale);
        
        // Draw map image
        if (this.mapImage) {
            this.ctx.drawImage(this.mapImage, 0, 0);
        }
        
        // Draw grid (optional, helps with orientation)
        this.drawGrid();
        
        // Draw robot
        this.drawRobot();
        
        this.ctx.restore();
        
        // Draw UI overlay
        this.drawOverlay();
    }
    
    drawGrid() {
        const gridSize = 50;
        this.ctx.strokeStyle = 'rgba(200, 200, 200, 0.2)';
        this.ctx.lineWidth = 1;
        
        for (let x = 0; x < this.canvas.width; x += gridSize) {
            this.ctx.beginPath();
            this.ctx.moveTo(x, 0);
            this.ctx.lineTo(x, this.canvas.height);
            this.ctx.stroke();
        }
        
        for (let y = 0; y < this.canvas.height; y += gridSize) {
            this.ctx.beginPath();
            this.ctx.moveTo(0, y);
            this.ctx.lineTo(this.canvas.width, y);
            this.ctx.stroke();
        }
    }
    
    drawRobot() {
        const x = this.robotPosition.x;
        const y = this.robotPosition.y;
        
        // Draw robot body (circle)
        this.ctx.fillStyle = '#2196F3';
        this.ctx.beginPath();
        this.ctx.arc(x, y, 15, 0, Math.PI * 2);
        this.ctx.fill();
        
        // Draw robot outline
        this.ctx.strokeStyle = '#1976D2';
        this.ctx.lineWidth = 2;
        this.ctx.stroke();
        
        // Draw direction indicator (front of robot)
        this.ctx.fillStyle = '#FFF';
        this.ctx.beginPath();
        this.ctx.arc(x + 8, y, 4, 0, Math.PI * 2);
        this.ctx.fill();
        
        // Draw position text
        this.ctx.fillStyle = '#333';
        this.ctx.font = '12px Arial';
        this.ctx.textAlign = 'center';
        this.ctx.fillText(`(${x.toFixed(0)}, ${y.toFixed(0)})`, x, y + 30);
    }
    
    drawOverlay() {
        // Draw zoom level
        this.ctx.fillStyle = '#333';
        this.ctx.font = '12px monospace';
        this.ctx.fillText(`Zoom: ${(this.scale * 100).toFixed(0)}%`, 10, 20);
        
        // Draw loading indicator
        if (this.isLoading) {
            document.getElementById('loading-indicator').style.display = 'flex';
        } else {
            document.getElementById('loading-indicator').style.display = 'none';
        }
    }
    
    updateStatusDisplay(state) {
        const timestamp = new Date().toLocaleTimeString();
        document.getElementById('timestamp-display').textContent = timestamp;
        document.getElementById('status-display').textContent = state.state || 'Unknown';
        document.getElementById('position-display').textContent = 
            `${this.robotPosition.x.toFixed(1)}, ${this.robotPosition.y.toFixed(1)}`;
    }
    
    showError(message) {
        const errorContainer = document.getElementById('error-container');
        errorContainer.innerHTML = `<div class="error">${message}</div>`;
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new RobotMapViewer();
});
