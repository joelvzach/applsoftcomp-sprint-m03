#!/usr/bin/env python3
"""
Progress Server - Real-time progress updates via Server-Sent Events (SSE).

Opens a browser window automatically and streams workflow progress updates.
"""

import json
import threading
import webbrowser
import socket
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict


class ProgressHandler(BaseHTTPRequestHandler):
    """HTTP handler for progress dashboard and SSE stream."""

    # Class-level storage for progress state
    progress_state: Dict = {}
    clients: List = []
    server_start_time: datetime = None

    def log_message(self, format, *args):
        """Suppress default HTTP server logging."""
        pass

    def do_GET(self):
        """Handle GET requests for dashboard and SSE stream."""

        if self.path == "/":
            self.serve_dashboard()
        elif self.path == "/events":
            self.serve_sse_stream()
        elif self.path == "/status":
            self.serve_status()
        elif self.path == "/session":
            self.serve_session()
        elif self.path.startswith("/map/"):
            self.serve_route_map()
        else:
            self.send_error(404, "Not Found")

    def serve_route_map(self):
        """Serve the route_viz.svg file from session folder with zoom/pan controls."""
        session_path = ProgressHandler.progress_state.get("session_path")
        if not session_path:
            print(f"[serve_route_map] ERROR: No session path configured")
            self.send_error(404, "No session path configured")
            return

        # Try to serve route_viz.svg (pre-rendered with route)
        map_file = Path(session_path) / "route_viz.svg"
        if not map_file.exists():
            print(f"[serve_route_map] ERROR: File not found: {map_file}")
            print(f"[serve_route_map] Session path: {session_path}")
            print(
                f"[serve_route_map] Files in session: {list(Path(session_path).iterdir()) if Path(session_path).exists() else 'Path does not exist'}"
            )
            self.send_error(404, "Route map not found")
            return

        print(f"[serve_route_map] Serving: {map_file}")

        # Read SVG content
        with open(map_file, "r") as f:
            svg_content = f.read()

        # Serve SVG wrapped in HTML with zoom/pan controls
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()

        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Route Map</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            background: #f5f5f5;
            padding: 20px;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{
            padding: 20px;
            background: #c41230;
            color: white;
        }}
        .header h1 {{ font-size: 24px; margin-bottom: 8px; }}
        .controls {{
            padding: 16px 20px;
            background: #f9f9f9;
            border-bottom: 1px solid #e0e0e0;
            display: flex;
            gap: 12px;
            align-items: center;
        }}
        .zoom-btn {{
            padding: 8px 16px;
            background: #007bff;
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
        }}
        .zoom-btn:hover {{ background: #0056b3; }}
        .zoom-level {{ margin-left: auto; font-size: 14px; color: #666; }}
        .map-container {{
            padding: 20px;
            overflow: auto;
            max-height: 70vh;
            cursor: move;
            background: white;
        }}
        .map-container svg {{
            transform-origin: 0 0;
            transition: transform 0.1s ease;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🗺️ Route Map</h1>
            <p>Target Binghamton Vestal - Optimized Shopping Route</p>
        </div>
        <div class="controls">
            <button class="zoom-btn" onclick="zoomIn()">🔍 Zoom In</button>
            <button class="zoom-btn" onclick="zoomOut()">🔎 Zoom Out</button>
            <button class="zoom-btn" onclick="resetZoom()">⟲ Reset</button>
            <span class="zoom-level" id="zoomLevel">100%</span>
        </div>
        <div class="map-container" id="mapContainer">
            {svg_content}
        </div>
    </div>
    <script>
        let zoom = 1;
        const mapContainer = document.getElementById('mapContainer');
        const svg = mapContainer.querySelector('svg');
        
        function updateZoom() {{
            if (svg) {{
                svg.style.transform = `scale(${{zoom}})`;
            }}
            document.getElementById('zoomLevel').textContent = Math.round(zoom * 100) + '%';
        }}
        
        function zoomIn() {{
            zoom = Math.min(zoom + 0.25, 3);
            updateZoom();
        }}
        
        function zoomOut() {{
            zoom = Math.max(zoom - 0.25, 0.25);
            updateZoom();
        }}
        
        function resetZoom() {{
            zoom = 1;
            updateZoom();
        }}
        
        // Pan functionality
        let isPanning = false;
        let startX, startY, scrollLeft, scrollTop;
        
        mapContainer.addEventListener('mousedown', (e) => {{
            isPanning = true;
            startX = e.pageX - mapContainer.offsetLeft;
            startY = e.pageY - mapContainer.offsetTop;
            scrollLeft = mapContainer.scrollLeft;
            scrollTop = mapContainer.scrollTop;
            mapContainer.style.cursor = 'grabbing';
        }});
        
        mapContainer.addEventListener('mouseleave', () => {{
            isPanning = false;
            mapContainer.style.cursor = 'move';
        }});
        
        mapContainer.addEventListener('mouseup', () => {{
            isPanning = false;
            mapContainer.style.cursor = 'move';
        }});
        
        mapContainer.addEventListener('mousemove', (e) => {{
            if (!isPanning) return;
            e.preventDefault();
            const x = e.pageX - mapContainer.offsetLeft;
            const y = e.pageY - mapContainer.offsetTop;
            const walkX = (x - startX) * 2;
            const walkY = (y - startY) * 2;
            mapContainer.scrollLeft = scrollLeft - walkX;
            mapContainer.scrollTop = scrollTop - walkY;
        }});
        
        // Mouse wheel zoom
        mapContainer.addEventListener('wheel', (e) => {{
            e.preventDefault();
            if (e.deltaY < 0) {{
                zoom = Math.min(zoom + 0.1, 3);
            }} else {{
                zoom = Math.max(zoom - 0.1, 0.25);
            }}
            updateZoom();
        }});
    </script>
</body>
</html>"""

        self.wfile.write(html.encode("utf-8"))

    def serve_session(self):
        """Serve session path as JSON."""
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()

        self.wfile.write(
            json.dumps(
                {"session_path": ProgressHandler.progress_state.get("session_path", "")}
            ).encode("utf-8")
        )

    def serve_dashboard(self):
        """Serve the progress dashboard HTML page."""
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()

        html = self.get_dashboard_html()
        self.wfile.write(html.encode("utf-8"))

    def serve_sse_stream(self):
        """Serve Server-Sent Events stream for real-time updates."""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()

        # Add client to list
        client = {"wfile": self.wfile, "connected": True}
        self.clients.append(client)

        print(f"[SSE] Client connected, sending init state")
        print(
            f"[SSE] Current tasks: {[(t['num'], t['status']) for t in ProgressHandler.progress_state['tasks']]}"
        )

        # Send initial state
        self.send_sse_event("init", ProgressHandler.progress_state)

        try:
            # Keep connection alive
            while client["connected"]:
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            print(f"[SSE] Client disconnected")
            client["connected"] = False

        # Remove client on disconnect
        if client in self.clients:
            self.clients.remove(client)

    def serve_status(self):
        """Serve current progress state as JSON."""
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()

        self.wfile.write(json.dumps(ProgressHandler.progress_state).encode("utf-8"))

    def send_sse_event(self, event_type: str, data: dict):
        """Send SSE event to all connected clients."""
        message = f"event: {event_type}\ndata: {json.dumps(data)}\n\n"

        for client in self.clients[:]:
            if client["connected"]:
                try:
                    client["wfile"].write(message.encode("utf-8"))
                    client["wfile"].flush()
                except (BrokenPipeError, ConnectionResetError):
                    client["connected"] = False

    @classmethod
    def broadcast_update(cls, data: dict):
        """Broadcast progress update to all connected clients."""
        cls.progress_state.update(data)

        event_type = data.get("type", "update")
        message = f"event: {event_type}\ndata: {json.dumps(data)}\n\n"

        connected_count = sum(1 for c in cls.clients if c.get("connected", False))
        print(
            f"[Broadcast] {event_type} → {connected_count}/{len(cls.clients)} clients connected"
        )

        for client in cls.clients[:]:
            if client["connected"]:
                try:
                    client["wfile"].write(message.encode("utf-8"))
                    client["wfile"].flush()
                except (BrokenPipeError, ConnectionResetError):
                    print(f"[Broadcast] Client disconnected")
                    client["connected"] = False

    def get_dashboard_html(self) -> str:
        """Generate progress dashboard HTML."""
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Target Shopper - Progress</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: #ffffff;
            color: #1a1a1a;
            padding: 40px;
            max-width: 900px;
            margin: 0 auto;
        }
        
        h1 {
            font-size: 28px;
            font-weight: 600;
            margin-bottom: 8px;
            color: #1a1a1a;
        }
        
        .subtitle {
            color: #666;
            font-size: 14px;
            margin-bottom: 32px;
        }
        
        .progress-container {
            margin-bottom: 32px;
        }
        
        .progress-bar-wrapper {
            background: #f0f0f0;
            border-radius: 8px;
            height: 12px;
            overflow: hidden;
            margin-bottom: 12px;
        }
        
        .progress-bar {
            background: linear-gradient(90deg, #007bff, #0056b3);
            height: 100%;
            width: 0%;
            transition: width 0.3s ease;
            border-radius: 8px;
        }
        
        .progress-text {
            font-size: 14px;
            color: #666;
            text-align: right;
        }
        
        .tasks {
            display: grid;
            gap: 12px;
            margin-bottom: 32px;
        }
        
        .task {
            display: flex;
            align-items: center;
            padding: 16px;
            background: #f8f9fa;
            border-radius: 8px;
            border: 1px solid #e9ecef;
            transition: all 0.2s ease;
        }
        
        .task.pending {
            opacity: 0.5;
        }
        
        .task.running {
            background: #e7f3ff;
            border-color: #007bff;
        }
        
        .task.complete {
            background: #e8f5e9;
            border-color: #4caf50;
        }
        
        .task.failed {
            background: #ffebee;
            border-color: #f44336;
        }
        
        .task-icon {
            width: 24px;
            height: 24px;
            margin-right: 16px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 16px;
        }
        
        .task-name {
            flex: 1;
            font-weight: 500;
        }
        
        .task-status {
            font-size: 12px;
            color: #666;
        }
        
        .task.running .task-status {
            color: #007bff;
        }
        
        .task.complete .task-status {
            color: #4caf50;
        }
        
        .task.failed .task-status {
            color: #f44336;
        }
        
        .log-container {
            background: #1a1a1a;
            color: #00ff00;
            border-radius: 8px;
            padding: 16px;
            font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace;
            font-size: 13px;
            line-height: 1.6;
            max-height: 300px;
            overflow-y: auto;
            margin-bottom: 32px;
        }
        
        .log-entry {
            margin-bottom: 4px;
        }
        
        .log-entry:last-child {
            margin-bottom: 0;
        }
        
        .log-entry.error {
            color: #ff6b6b;
        }
        
        .log-entry.success {
            color: #51cf66;
        }
        
        .log-entry.info {
            color: #007bff;
        }
        
        .final-actions {
            display: none;
            text-align: center;
            padding: 32px;
            background: #e8f5e9;
            border-radius: 8px;
            border: 1px solid #4caf50;
        }
        
        .final-actions.visible {
            display: block;
        }
        
        .final-actions h2 {
            font-size: 20px;
            margin-bottom: 16px;
            color: #2e7d32;
        }
        
        .final-actions p {
            margin-bottom: 24px;
            color: #666;
        }
        
        .btn {
            display: inline-block;
            padding: 12px 32px;
            background: #007bff;
            color: white;
            text-decoration: none;
            border-radius: 6px;
            font-weight: 500;
            font-size: 14px;
            transition: background 0.2s ease;
            border: none;
            cursor: pointer;
        }
        
        .btn:hover {
            background: #0056b3;
        }
        
        .btn-success {
            background: #4caf50;
        }
        
        .btn-success:hover {
            background: #43a047;
        }
        
        .btn-close {
            background: #666;
            margin-left: 12px;
        }
        
        .btn-close:hover {
            background: #555;
        }
        
        /* Map Overlay Styles */
        .map-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.8);
            z-index: 9999;
            display: none;
            align-items: center;
            justify-content: center;
        }
        
        .map-overlay-content {
            background: white;
            width: 95%;
            height: 95%;
            border-radius: 8px;
            overflow: hidden;
            display: flex;
            flex-direction: column;
        }
        
        .map-overlay-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 16px 24px;
            background: #f8f9fa;
            border-bottom: 1px solid #e9ecef;
        }
        
        .map-overlay-header h3 {
            margin: 0;
            font-size: 18px;
            color: #1a1a1a;
        }
        
        .map-close-btn {
            background: #666;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            transition: background 0.2s;
        }
        
        .map-close-btn:hover {
            background: #555;
        }
        
        #mapFrame {
            flex: 1;
            width: 100%;
            border: none;
        }
        
        #mapFrame:not([src]) {
            background: #f5f5f5;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #666;
        }
        
        .spinner {
            display: inline-block;
            width: 16px;
            height: 16px;
            border: 2px solid #f3f3f3;
            border-top: 2px solid #007bff;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    
        .searching-items {
            padding: 16px 20px;
            background: #e7f3ff;
            border: 1px solid #007bff;
            border-radius: 8px;
            margin-bottom: 24px;
        }
        
        .searching-items h3 {
            font-size: 14px;
            color: #666;
            margin-bottom: 12px;
        }
        
        .item-tags {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }
        
        .item-tag {
            padding: 6px 12px;
            background: #e9ecef;
            border-radius: 16px;
            font-size: 13px;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        
        .item-tag.searching {
            background: #e7f3ff;
            color: #007bff;
        }
        
        .item-tag.found {
            background: #e8f5e9;
            color: #4caf50;
        }
        
        .item-tag.missing {
            background: #ffebee;
            color: #f44336;
        }
        
        .btn-info {
            background: #17a2b8;
        }
        
        .btn-info:hover {
            background: #138496;
        }
        
        /* Modal Styles */
        .modal-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.5);
            z-index: 10000;
            display: none;
            align-items: center;
            justify-content: center;
        }
        
        .modal-content {
            background: white;
            border-radius: 8px;
            width: 90%;
            max-width: 800px;
            max-height: 80vh;
            overflow: hidden;
            display: flex;
            flex-direction: column;
        }
        
        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 16px 24px;
            background: #f8f9fa;
            border-bottom: 1px solid #e9ecef;
        }
        
        .modal-header h3 {
            margin: 0;
            font-size: 18px;
        }
        
        .modal-close {
            background: none;
            border: none;
            font-size: 24px;
            cursor: pointer;
            color: #666;
            padding: 0;
            width: 32px;
            height: 32px;
        }
        
        .modal-close:hover {
            color: #000;
        }
        
        .modal-body {
            padding: 24px;
            overflow-y: auto;
        }
        
        .items-table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
        }
        
        .items-table th,
        .items-table td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #e9ecef;
        }
        
        .items-table th {
            background: #f8f9fa;
            font-weight: 600;
            color: #555;
        }
        
        .items-table tr:hover {
            background: #f8f9fa;
        }
        
        .items-summary {
            padding: 16px;
            background: #f8f9fa;
            border-radius: 6px;
            text-align: center;
        }
        
        .items-summary strong {
            font-size: 16px;
            color: #1a1a1a;
        }
</style>
</head>
<body>
    <div class="searching-items" id="searchingItems" style="display: none;">
        <h3>🔍 Searching for:</h3>
        <div class="item-tags" id="itemTags"></div>
    </div>

    <h1>🎯 Target Shopper</h1>
    <p class="subtitle">Grocery Route Optimizer - Progress Dashboard</p>
    
    <div class="progress-container">
        <div class="progress-bar-wrapper">
            <div class="progress-bar" id="progressBar"></div>
        </div>
        <div class="progress-text" id="progressText">Initializing...</div>
    </div>
    
    <div class="tasks" id="tasksList">
        <!-- Tasks will be populated dynamically -->
    </div>
    
    <div class="log-container" id="logContainer">
        <!-- Log entries will be appended here -->
    </div>
    
    <div class="final-actions" id="finalActions">
        <h2>✅ Workflow Complete!</h2>
        <p id="finalSummary"></p>
        <button class="btn btn-success" onclick="openMapOverlay()">🗺️ View Map</button>
        <button class="btn btn-info" onclick="openItemsModal()" id="viewItemsBtn">📋 View Items & Prices</button>
        <button class="btn btn-close" onclick="closeWindow()">✕ Close</button>
    </div>
    
    <!-- Map Overlay Modal -->
    <div id="mapOverlay" class="map-overlay" style="display: none;">
        <div class="map-overlay-content">
            <div class="map-overlay-header">
                <h3>🗺️ Interactive Route Map</h3>
                <button class="map-close-btn" onclick="closeMapOverlay()">✕ Close Map</button>
            </div>
            <iframe id="mapFrame" src="" frameborder="0"></iframe>
        </div>
    </div>
    
    <script>
        const eventSource = new EventSource('/events');
        let tasks = [];
        let logs = [];
        
        eventSource.addEventListener('init', (event) => {
            const data = JSON.parse(event.data);
            if (data.tasks) {
                tasks = data.tasks;
                renderTasks();
            }
        });
        
        eventSource.addEventListener('update', (event) => {
            const data = JSON.parse(event.data);
            handleUpdate(data);
            // Recalculate progress from task statuses
            updateProgressFromTasks();
        });
        
        eventSource.addEventListener('task_start', (event) => {
            const data = JSON.parse(event.data);
            updateTaskStatus(data.taskNum, 'running', data.message);
            updateProgressFromTasks();
        });
        
        eventSource.addEventListener('task_complete', (event) => {
            const data = JSON.parse(event.data);
            console.log('Task complete:', data.taskNum, data.message);
            updateTaskStatus(data.taskNum, 'complete', data.message);
            updateProgressFromTasks();
        });
        
        eventSource.addEventListener('task_failed', (event) => {
            const data = JSON.parse(event.data);
            updateTaskStatus(data.taskNum, 'failed', data.message);
            updateProgressFromTasks();
        });
        
        function updateProgressFromTasks() {
            const completed = tasks.filter(t => t.status === 'complete').length;
            const failed = tasks.filter(t => t.status === 'failed').length;
            const total = tasks.length;
            const progress = ((completed + failed) / total) * 100;
            updateProgressBar(progress, `${completed}/${total} tasks complete`);
        }
        
        eventSource.addEventListener('log', (event) => {
            const data = JSON.parse(event.data);
            addLogEntry(data.message, data.level);
        });
        
        eventSource.addEventListener('complete', (event) => {
            const data = JSON.parse(event.data);
            // Mark task 6 as complete
            updateTaskStatus(6, 'complete', 'Done');
            updateProgressFromTasks();
            showFinalActions(data);
        });
        
        eventSource.addEventListener('error', (event) => {
            const data = JSON.parse(event.data);
            addLogEntry(data.message, 'error');
        });
        
        eventSource.addEventListener('items_set', (event) => {
            const data = JSON.parse(event.data);
            displayItems(data.items);
        });
        
        eventSource.addEventListener('items_updated', (event) => {
            const data = JSON.parse(event.data);
            console.log('Items updated:', data.results);
            updateItemsWithResults(data.results);
            // Store for modal access
            window.itemsData = data.results;
        });
        
        eventSource.addEventListener('items_set', (event) => {
            const data = JSON.parse(event.data);
            console.log('Items set:', data.items);
            displayItems(data.items);
            // Initialize empty items data
            window.itemsData = [];
        });
        
        function displayItems(items) {
            const container = document.getElementById('searchingItems');
            const tagsContainer = document.getElementById('itemTags');
            
            if (!container || !tagsContainer) return;
            
            container.style.display = 'block';
            tagsContainer.innerHTML = '';
            
            items.forEach((item, index) => {
                const tag = document.createElement('div');
                tag.className = 'item-tag searching';
                tag.id = `item-tag-${index}`;
                tag.innerHTML = `<span>⏳</span> <span>${item}</span>`;
                tagsContainer.appendChild(tag);
            });
            
            // Show View Items button immediately
            const viewItemsBtn = document.getElementById('viewItemsBtn');
            if (viewItemsBtn) {
                viewItemsBtn.style.display = 'inline-block';
            }
        }
        
        function updateItemsWithResults(results) {
            const tagsContainer = document.getElementById('itemTags');
            const viewItemsBtn = document.getElementById('viewItemsBtn');
            
            if (!tagsContainer) return;
            
            results.forEach((result, index) => {
                const tag = document.getElementById(`item-tag-${index}`);
                if (tag) {
                    if (result.available) {
                        tag.className = 'item-tag found';
                        tag.innerHTML = `<span>✅</span> <span>${result.item}</span>`;
                    } else {
                        tag.className = 'item-tag missing';
                        tag.innerHTML = `<span>❌</span> <span>${result.item}</span>`;
                    }
                }
            });
            
            // Show View Items button
            if (viewItemsBtn) {
                viewItemsBtn.style.display = 'inline-block';
                populateItemsTable(results);
            }
        }
        
        function populateItemsTable(results) {
            const tbody = document.getElementById('itemsTableBody');
            const summary = document.getElementById('itemsSummary');
            
            if (!tbody) return;
            
            tbody.innerHTML = '';
            
            let totalCost = 0;
            let foundCount = 0;
            
            results.forEach(result => {
                const row = document.createElement('tr');
                
                const status = result.available ? 
                    '<span style="color: #4caf50;">✅ Found</span>' : 
                    '<span style="color: #f44336;">❌ Not found</span>';
                
                const price = result.price ? `$${result.price.toFixed(2)}` : 'N/A';
                const aisle = result.aisle || 'N/A';
                const productUrl = result.product_url || '#';
                const productLink = result.available && productUrl !== '#' ? 
                    `<a href="${productUrl}" target="_blank" style="color: #007bff; text-decoration: none;">🔗 View</a>` : 
                    'N/A';
                
                if (result.available) {
                    totalCost += result.price || 0;
                    foundCount++;
                }
                
                row.innerHTML = `
                    <td>${result.item}</td>
                    <td>${aisle}</td>
                    <td>${price}</td>
                    <td>${productLink}</td>
                    <td>${status}</td>
                `;
                tbody.appendChild(row);
            });
            
            if (summary) {
                summary.innerHTML = `
                    <strong>Found: ${foundCount}/${results.length} items | Total: $${totalCost.toFixed(2)}</strong>
                `;
            }
        }
        
        function openItemsModal() {
            const modal = document.getElementById('itemsModal');
            if (modal) {
                console.log('Opening items modal');
                // Populate with stored data if available
                if (window.itemsData && window.itemsData.length > 0) {
                    populateItemsTable(window.itemsData);
                }
                modal.style.display = 'flex';
            } else {
                console.error('Items modal not found');
            }
        }
        
        function closeItemsModal() {
            const modal = document.getElementById('itemsModal');
            if (modal) {
                modal.style.display = 'none';
            }
        }
        
        // Close modal when clicking outside
        window.onclick = function(event) {
            const modal = document.getElementById('itemsModal');
            if (event.target == modal) {
                modal.style.display = 'none';
            }
        }

        
        function handleUpdate(data) {
            if (data.progress !== undefined) {
                updateProgressBar(data.progress, data.message);
            }
            if (data.tasks) {
                tasks = data.tasks;
                renderTasks();
            }
        }
        
        // Force progress update after any task change
        function forceProgressUpdate() {
            updateProgressFromTasks();
        }
        
        function updateProgressBar(progress, message) {
            const bar = document.getElementById('progressBar');
            const text = document.getElementById('progressText');
            bar.style.width = progress + '%';
            text.textContent = message || Math.round(progress) + '% complete';
        }
        
        function updateTaskStatus(taskNum, status, message) {
            const taskEl = document.querySelector(`.task[data-task="${taskNum}"]`);
            if (taskEl) {
                taskEl.className = `task ${status}`;
                const statusEl = taskEl.querySelector('.task-status');
                const iconEl = taskEl.querySelector('.task-icon');
                if (statusEl) {
                    statusEl.textContent = message || getStatusText(status);
                }
                if (iconEl) {
                    iconEl.innerHTML = getTaskIcon(status);
                }
            }
            // Also update tasks array for progress calculation
            const task = tasks.find(t => t.num === taskNum);
            if (task) {
                task.status = status;
                task.message = message || getStatusText(status);
            }
        }
        
        function getStatusText(status) {
            switch(status) {
                case 'running': return 'In progress...';
                case 'complete': return 'Done';
                case 'failed': return 'Failed';
                default: return 'Pending';
            }
        }
        
        function addLogEntry(message, level = 'info') {
            const container = document.getElementById('logContainer');
            const entry = document.createElement('div');
            entry.className = `log-entry ${level}`;
            const timestamp = new Date().toLocaleTimeString();
            entry.textContent = `[${timestamp}] ${message}`;
            container.appendChild(entry);
            container.scrollTop = container.scrollHeight;
        }
        
        function renderTasks() {
            const container = document.getElementById('tasksList');
            container.innerHTML = '';
            
            tasks.forEach(task => {
                const taskEl = document.createElement('div');
                taskEl.className = `task ${task.status || 'pending'}`;
                taskEl.setAttribute('data-task', task.num);
                taskEl.innerHTML = `
                    <div class="task-icon">${getTaskIcon(task.status)}</div>
                    <div class="task-name">${task.name}</div>
                    <div class="task-status">${task.message || 'Pending'}</div>
                `;
                container.appendChild(taskEl);
            });
        }
        
        function getTaskIcon(status) {
            switch(status) {
                case 'running': return '<span class="spinner"></span>';
                case 'complete': return '✅';
                case 'failed': return '❌';
                default: return '⭕';
            }
        }
        
        function showFinalActions(data) {
            const actions = document.getElementById('finalActions');
            const summary = document.getElementById('finalSummary');
            actions.classList.add('visible');
            
            if (data.summary) {
                summary.textContent = data.summary;
            }
        }
        
        function openMapOverlay() {
            // Open map in overlay modal
            const overlay = document.getElementById('mapOverlay');
            const frame = document.getElementById('mapFrame');
            
            console.log('Opening map overlay...');
            console.log('Map frame exists:', frame !== null);
            console.log('Overlay exists:', overlay !== null);
            
            if (!frame || !overlay) {
                console.error('Map frame or overlay not found in DOM');
                alert('Map container not found. Please refresh the page.');
                return;
            }
            
            // Clear previous src to force reload
            frame.src = '';
            
            // Add load event handlers BEFORE setting src
            frame.onload = () => {
                console.log('✓ Map loaded successfully');
                console.log('  Frame URL:', frame.src);
                console.log('  Frame content window:', frame.contentWindow !== null);
            };
            
            frame.onerror = () => {
                console.error('✗ Map load error');
                alert('Map could not be loaded. Please check the browser console for details.');
            };
            
            // Add timestamp to prevent caching
            const mapUrl = '/map/?t=' + Date.now();
            console.log('Loading map from:', mapUrl);
            
            // Set src and show overlay
            frame.src = mapUrl;
            overlay.style.display = 'flex';
            
            console.log('Overlay display set to flex');
        }
        
        function closeMapOverlay() {
            const overlay = document.getElementById('mapOverlay');
            const frame = document.getElementById('mapFrame');
            frame.src = '';
            overlay.style.display = 'none';
        }
        
        function closeWindow() {
            window.close();
        }
        
        // Initialize with default tasks
        tasks = [
            { num: 1, name: 'Store Configuration', status: 'pending' },
            { num: 2, name: 'Item Search', status: 'pending' },
            { num: 3, name: 'Load Store Map', status: 'pending' },
            { num: 4, name: 'Route Optimization', status: 'pending' },
            { num: 5, name: 'Generate Outputs', status: 'pending' },
            { num: 6, name: 'Complete', status: 'pending' }
        ];
        renderTasks();
    </script>

    <!-- Items Modal -->
    <div id="itemsModal" class="modal-overlay" style="display: none;">
        <div class="modal-content">
            <div class="modal-header">
                <h3>📋 Items & Prices</h3>
                <button class="modal-close" onclick="closeItemsModal()">✕</button>
            </div>
            <div class="modal-body">
                <table class="items-table">
                    <thead>
                        <tr>
                            <th>Item</th>
                            <th>Aisle</th>
                            <th>Price</th>
                            <th>Product</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody id="itemsTableBody">
                    </tbody>
                </table>
                <div class="items-summary" id="itemsSummary">
                </div>
            </div>
        </div>
    </div>
</body>
</html>"""


class ProgressServer:
    """Progress server that broadcasts updates via SSE."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8000):
        self.host = host
        self.port = port
        self.server: Optional[HTTPServer] = None
        self.thread: Optional[threading.Thread] = None
        self.session_path: Optional[str] = None

        # Initialize progress state
        ProgressHandler.progress_state = {
            "progress": 0,
            "message": "Initializing...",
            "tasks": [
                {"num": 1, "name": "Store Configuration", "status": "pending"},
                {"num": 2, "name": "Item Search", "status": "pending"},
                {"num": 3, "name": "Load Store Map", "status": "pending"},
                {"num": 4, "name": "Route Optimization", "status": "pending"},
                {"num": 5, "name": "Generate Outputs", "status": "pending"},
                {"num": 6, "name": "Complete", "status": "pending"},
            ],
            "logs": [],
            "complete": False,
        }
        ProgressHandler.clients = []

    def start(self, open_browser: bool = True):
        """Start the progress server in a background thread."""

        # Find available port
        actual_port = self.port
        while True:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind((self.host, actual_port))
                    break
            except OSError:
                actual_port += 1

        self.port = actual_port
        self.server = HTTPServer((self.host, self.port), ProgressHandler)

        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.daemon = True
        self.thread.start()

        # Open browser automatically
        if open_browser:
            url = f"http://{self.host}:{self.port}/"
            webbrowser.open(url)
            print(f"🌐 Progress dashboard opened: {url}")
        else:
            print(
                f"🌐 Progress dashboard available at: http://{self.host}:{self.port}/"
            )

    def stop(self):
        """Stop the progress server."""
        if self.server:
            self.server.shutdown()
            self.thread.join(timeout=2)
            self.server.server_close()

    def update(
        self,
        task_num: int = None,
        status: str = None,
        message: str = None,
        progress: float = None,
        log_entry: str = None,
        log_level: str = "info",
    ):
        """Send progress update to all connected clients."""

        update_data = {}

        if task_num is not None and status is not None:
            # Update task status
            for task in ProgressHandler.progress_state["tasks"]:
                if task["num"] == task_num:
                    task["status"] = status
                    if message:
                        task["message"] = message
                    break

            # Broadcast task update
            event_type = f"task_{status}"
            ProgressHandler.broadcast_update(
                {
                    "type": event_type,
                    "taskNum": task_num,
                    "message": message,
                }
            )

        if progress is not None:
            update_data["progress"] = progress
            if message:
                update_data["message"] = message

        if log_entry:
            ProgressHandler.progress_state["logs"].append(
                {
                    "message": log_entry,
                    "level": log_level,
                    "timestamp": datetime.now().isoformat(),
                }
            )
            ProgressHandler.broadcast_update(
                {
                    "type": "log",
                    "message": log_entry,
                    "level": log_level,
                }
            )

        if update_data:
            ProgressHandler.broadcast_update({"type": "update", **update_data})

    def set_session_path(self, path: str):
        """Set the session folder path for final report access."""
        self.session_path = str(path)
        ProgressHandler.progress_state["session_path"] = str(path)

    def set_items(self, items: list):
        """Set the list of items being searched."""
        self.items = items
        ProgressHandler.progress_state["items"] = items
        # Broadcast to connected clients
        ProgressHandler.broadcast_update({"type": "items_set", "items": items})

    def update_items_with_results(self, results: list):
        """Update items with search results."""
        ProgressHandler.progress_state["search_results"] = results
        ProgressHandler.broadcast_update({"type": "items_updated", "results": results})

    def complete(self, summary: str = None):
        """Mark workflow as complete."""
        ProgressHandler.progress_state["complete"] = True
        ProgressHandler.broadcast_update(
            {
                "type": "complete",
                "summary": summary,
                "session_path": self.session_path,
            }
        )

    def task_start(self, task_num: int, message: str = "Starting..."):
        """Mark a task as started."""
        self.update(task_num=task_num, status="running", message=message)

    def task_complete(self, task_num: int, message: str = "Complete"):
        """Mark a task as complete."""
        self.update(task_num=task_num, status="complete", message=message)

    def task_failed(self, task_num: int, message: str = "Failed"):
        """Mark a task as failed."""
        self.update(task_num=task_num, status="failed", message=message)

    def log(self, message: str, level: str = "info"):
        """Add a log entry."""
        self.update(log_entry=message, log_level=level)


# Global progress server instance
_progress_server: Optional[ProgressServer] = None


def get_progress_server() -> Optional[ProgressServer]:
    """Get the global progress server instance."""
    return _progress_server


def init_progress_server(port: int = 8000, open_browser: bool = True) -> ProgressServer:
    """Initialize and start the global progress server."""
    global _progress_server
    _progress_server = ProgressServer(port=port)
    _progress_server.start(open_browser=open_browser)
    return _progress_server
