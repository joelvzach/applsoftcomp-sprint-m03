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
        """Serve the route_map.html file from session folder."""
        session_path = ProgressHandler.progress_state.get("session_path")
        if not session_path:
            self.send_error(404, "No session path configured")
            return

        map_file = Path(session_path) / "route_map.html"
        if not map_file.exists():
            self.send_error(404, "Route map not found")
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()

        with open(map_file, "rb") as f:
            self.wfile.write(f.read())

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

        # Send initial state
        self.send_sse_event("init", ProgressHandler.progress_state)

        try:
            # Keep connection alive
            while client["connected"]:
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
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

        for client in cls.clients[:]:
            if client["connected"]:
                try:
                    client["wfile"].write(message.encode("utf-8"))
                    client["wfile"].flush()
                except (BrokenPipeError, ConnectionResetError):
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
    </style>
</head>
<body>
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
        <button class="btn btn-success" onclick="openMapOverlay()">🗺️ View Interactive Map</button>
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
        });
        
        eventSource.addEventListener('task_start', (event) => {
            const data = JSON.parse(event.data);
            updateTaskStatus(data.taskNum, 'running', data.message);
            updateProgressFromTasks();
        });
        
        eventSource.addEventListener('task_complete', (event) => {
            const data = JSON.parse(event.data);
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
            showFinalActions(data);
        });
        
        eventSource.addEventListener('error', (event) => {
            const data = JSON.parse(event.data);
            addLogEntry(data.message, 'error');
        });
        
        function handleUpdate(data) {
            if (data.progress !== undefined) {
                updateProgressBar(data.progress, data.message);
            }
            if (data.tasks) {
                tasks = data.tasks;
                renderTasks();
            }
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
            frame.src = '/map/';
            overlay.style.display = 'flex';
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
            { num: 2, name: 'Parallel Item Search', status: 'pending' },
            { num: 3, name: 'Load Cached Store Map', status: 'pending' },
            { num: 4, name: 'Route Optimizer', status: 'pending' },
            { num: 5, name: 'Route Visualizer', status: 'pending' },
            { num: 6, name: 'Report Generator', status: 'pending' },
            { num: 7, name: 'HTML Map Generator', status: 'pending' },
            { num: 8, name: 'Output Summary', status: 'pending' }
        ];
        renderTasks();
    </script>
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
                {"num": 2, "name": "Parallel Item Search", "status": "pending"},
                {"num": 3, "name": "Load Cached Store Map", "status": "pending"},
                {"num": 4, "name": "Route Optimizer", "status": "pending"},
                {"num": 5, "name": "Route Visualizer", "status": "pending"},
                {"num": 6, "name": "Report Generator", "status": "pending"},
                {"num": 7, "name": "HTML Map Generator", "status": "pending"},
                {"num": 8, "name": "Output Summary", "status": "pending"},
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
