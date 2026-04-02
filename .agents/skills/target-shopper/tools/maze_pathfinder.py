#!/usr/bin/env python3
"""
Maze Pathfinder - A* pathfinding through walkability grid.
8-directional movement with configurable heuristics.
"""

import heapq
import numpy as np
from typing import List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class PathNode:
    """A* search node with direction tracking for turn minimization."""
    cell: Tuple[int, int]
    g_score: float
    f_score: float
    parent: Optional['PathNode'] = None
    direction: Tuple[int, int] = None  # Direction we arrived from
    
    def __lt__(self, other):
        return self.f_score < other.f_score


# 4-directional movement costs (orthogonal only - no diagonals)
# This ensures paths follow realistic 90-degree turns like a person would walk
# Turn penalty encourages straight paths with fewer turns
TURN_PENALTY = 2.0  # Additional cost for changing direction (higher = fewer turns)

DIRECTIONS = [
    (-1, 0, 1.0),    # North
    (1, 0, 1.0),     # South
    (0, -1, 1.0),    # West
    (0, 1, 1.0),     # East
]


def heuristic(cell1: Tuple[int, int], cell2: Tuple[int, int], method: str = 'euclidean') -> float:
    """
    Calculate heuristic distance between two cells.
    
    Methods:
    - euclidean: Straight-line distance (most accurate)
    - manhattan: Grid-based distance (faster)
    - chebyshev: Max of dx/dy (good for 8-directional)
    """
    dy = abs(cell1[0] - cell2[0])
    dx = abs(cell1[1] - cell2[1])
    
    if method == 'manhattan':
        return dx + dy
    elif method == 'chebyshev':
        return max(dx, dy)
    else:  # euclidean
        return np.sqrt(dx**2 + dy**2)


def get_neighbors(
    cell: Tuple[int, int],
    grid: np.ndarray
) -> List[Tuple[Tuple[int, int], float]]:
    """
    Get walkable neighbors of cell (orthogonal only).
    Returns list of (neighbor_cell, movement_cost).
    
    Cost multipliers based on walkability:
    - 1.0 (Floor-Pads): 1.0x cost (preferred)
    - 0.7 (open floor): 1.2x cost (acceptable)
    - 0.3 (Registers): 3.0x cost (avoid unless necessary)
    - 0.0 (obstacles): not walkable
    """
    row, col = cell
    height, width = grid.shape
    neighbors = []
    
    for dr, dc, cost in DIRECTIONS:
        new_row = row + dr
        new_col = col + dc
        
        # Check bounds
        if 0 <= new_row < height and 0 <= new_col < width:
            walkability = grid[new_row, new_col]
            
            # Check if walkable (anything > 0.0)
            if walkability > 0.0:
                # Apply cost multiplier based on walkability level
                if walkability >= 1.0:
                    # Floor-Pads (light grey) - preferred walking corridors
                    multiplier = 1.0
                elif walkability >= 0.7:
                    # Open floor - acceptable but not preferred
                    multiplier = 1.2
                elif walkability >= 0.3:
                    # Register-Shapes (dark grey) - avoid unless necessary
                    multiplier = 3.0
                else:
                    # Very low walkability - strong penalty
                    multiplier = 5.0
                
                neighbors.append(((new_row, new_col), cost * multiplier))
    
    return neighbors


def astar_search(
    grid: np.ndarray,
    start: Tuple[int, int],
    goal: Tuple[int, int],
    heuristic_method: str = 'euclidean'
) -> List[Tuple[int, int]]:
    """
    A* pathfinding algorithm with turn minimization.
    
    Args:
        grid: Walkability grid (0=obstacle, 1=walkable)
        start: Starting cell (row, col)
        goal: Goal cell (row, col)
        heuristic_method: 'euclidean', 'manhattan', or 'chebyshev'
    
    Returns:
        List of cells from start to goal, or empty list if no path
    """
    # Validate start and goal
    if not (0 <= start[0] < grid.shape[0] and 0 <= start[1] < grid.shape[1]):
        return []
    if not (0 <= goal[0] < grid.shape[0] and 0 <= goal[1] < grid.shape[1]):
        return []
    if grid[start[0], start[1]] <= 0.5:
        return []
    if grid[goal[0], goal[1]] <= 0.5:
        return []
    
    # Initialize search - start with no direction (None)
    start_node = PathNode(
        cell=start,
        g_score=0.0,
        f_score=heuristic(start, goal, heuristic_method),
        parent=None,
        direction=None
    )
    
    open_set = [start_node]
    closed_set = set()
    all_nodes = {start: start_node}
    
    while open_set:
        # Get node with lowest f_score
        current = heapq.heappop(open_set)
        
        if current.cell == goal:
            # Reconstruct path
            path = []
            node = current
            while node:
                path.append(node.cell)
                node = node.parent
            return list(reversed(path))
        
        closed_set.add(current.cell)
        
        # Explore neighbors
        for neighbor, cost in get_neighbors(current.cell, grid):
            if neighbor in closed_set:
                continue
            
            # Calculate direction to neighbor
            dr = neighbor[0] - current.cell[0]
            dc = neighbor[1] - current.cell[1]
            direction = (dr, dc)
            
            # Add turn penalty if changing direction
            turn_cost = 0.0
            if current.direction is not None and current.direction != direction:
                turn_cost = TURN_PENALTY
            
            tentative_g = current.g_score + cost + turn_cost
            
            # Check if we found a better path
            if neighbor not in all_nodes or tentative_g < all_nodes[neighbor].g_score:
                if neighbor not in all_nodes:
                    new_node = PathNode(
                        cell=neighbor,
                        g_score=tentative_g,
                        f_score=tentative_g + heuristic(neighbor, goal, heuristic_method),
                        parent=current,
                        direction=direction
                    )
                    all_nodes[neighbor] = new_node
                    heapq.heappush(open_set, new_node)
                else:
                    # Update existing node
                    all_nodes[neighbor].g_score = tentative_g
                    all_nodes[neighbor].f_score = tentative_g + heuristic(neighbor, goal, heuristic_method)
                    all_nodes[neighbor].parent = current
                    all_nodes[neighbor].direction = direction
                    # Re-heapify (expensive but correct)
                    open_set = list(all_nodes.values())
                    heapq.heapify(open_set)
    
    # No path found
    return []


def snap_to_walkable(maze, cell: Tuple[int, int], max_distance: int = 5) -> Tuple[int, int]:
    """
    Snap a cell to nearest walkable cell using BFS.
    """
    if maze.is_walkable(cell):
        return cell
    
    # BFS to find nearest walkable cell
    from collections import deque
    queue = deque([(cell, 0)])
    visited = {cell}
    
    while queue:
        current, dist = queue.popleft()
        
        if dist > max_distance:
            return cell  # Give up if too far
        
        if maze.is_walkable(current):
            return current
        
        row, col = current
        for dr, dc, _ in DIRECTIONS[:4]:  # Only orthogonal
            neighbor = (row + dr, col + dc)
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, dist + 1))
    
    return cell


def find_maze_path(
    maze,
    start: Tuple[float, float],
    goal: Tuple[float, float],
    waypoints: List[Tuple[float, float]] = None,
    heuristic_method: str = 'euclidean'
) -> List[Tuple[float, float]]:
    """
    Find path through maze from start to goal, optionally via waypoints.
    Snaps waypoints to nearest walkable cells.
    """
    # Convert to grid coordinates and snap to walkable
    start_cell = snap_to_walkable(maze, maze.world_to_grid(start))
    goal_cell = snap_to_walkable(maze, maze.world_to_grid(goal))
    
    # Build waypoint sequence (snap each to walkable)
    all_points = [start_cell]
    if waypoints:
        for wp in waypoints:
            wp_cell = maze.world_to_grid(wp)
            snapped = snap_to_walkable(maze, wp_cell, max_distance=8)
            all_points.append(snapped)
    all_points.append(goal_cell)
    
    # Find path through each segment
    full_path = []
    for i in range(len(all_points) - 1):
        segment = astar_search(
            maze.grid,
            all_points[i],
            all_points[i + 1],
            heuristic_method
        )
        
        if not segment:
            # Fallback: straight line
            print(f"Warning: No path found for segment {i}, using straight line")
            segment = generate_straight_line(all_points[i], all_points[i + 1])
        
        # Add segment (avoid duplicating waypoints)
        if full_path:
            full_path.extend(segment[1:])
        else:
            full_path.extend(segment)
    
    # Convert back to world coordinates
    world_path = [maze.grid_to_world(cell) for cell in full_path]
    
    return world_path


def generate_straight_line(
    start: Tuple[int, int],
    goal: Tuple[int, int]
) -> List[Tuple[int, int]]:
    """
    Generate straight line between two points (Bresenham's algorithm).
    Used as fallback when A* fails.
    """
    points = []
    
    x0, y0 = start[1], start[0]
    x1, y1 = goal[1], goal[0]
    
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    
    if dx > dy:
        err = dx // 2
        while x0 != x1:
            points.append((y0, x0))
            err -= dy
            if err < 0:
                y0 += sy
                err += dx
            x0 += sx
    else:
        err = dy // 2
        while y0 != y1:
            points.append((y0, x0))
            err -= dx
            if err < 0:
                x0 += sx
                err += dy
            y0 += sy
    
    points.append((y1, x1))
    return points


def calculate_path_length(path: List[Tuple[float, float]]) -> float:
    """Calculate total length of path in world coordinates."""
    if len(path) < 2:
        return 0.0
    
    total = 0.0
    for i in range(len(path) - 1):
        x1, y1 = path[i]
        x2, y2 = path[i + 1]
        total += np.sqrt((x2 - x1)**2 + (y2 - y1)**2)
    
    return total


if __name__ == '__main__':
    # Test with simple grid
    test_grid = np.ones((20, 20), dtype=np.float32)
    
    # Add obstacle in middle
    test_grid[8:12, 8:12] = 0.0
    
    start = (2, 2)
    goal = (18, 18)
    
    print("Testing A* pathfinding...")
    path = astar_search(test_grid, start, goal, 'euclidean')
    
    if path:
        print(f"Path found: {len(path)} cells")
        print(f"Start: {path[0]}, Goal: {path[-1]}")
    else:
        print("No path found")
