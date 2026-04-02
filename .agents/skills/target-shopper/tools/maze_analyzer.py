#!/usr/bin/env python3
"""
Maze Analyzer - Convert SVG store map to walkability grid.
Resolution: 0.05 SVG units (~5cm per cell)
"""

import re
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class StoreViewBox:
    x: float
    y: float
    width: float
    height: float


class StoreMaze:
    """
    Represents store layout as walkability grid.
    0.0 = obstacle (aisle shelves)
    1.0 = walkable (corridors, floor areas)
    """
    
    resolution = 0.3  # 30cm per cell (optimized for speed, still accurate enough)
    
    def __init__(self, svg_content: str):
        self.svg_content = svg_content
        self.viewBox = self._parse_viewbox(svg_content)
        self.aisle_labels = self._extract_aisle_labels(svg_content)
        self.special_locations = self._extract_special_locations(svg_content)
        
        # Pre-calculate grid dimensions
        self.grid_width = int(self.viewBox.width / self.resolution) + 1
        self.grid_height = int(self.viewBox.height / self.resolution) + 1
        
        self.grid = self._build_walkability_grid(svg_content)
    
    def _parse_viewbox(self, svg_content: str) -> StoreViewBox:
        """Extract viewBox attributes from SVG."""
        match = re.search(r'viewBox="([^"]+)"', svg_content)
        if match:
            parts = match.group(1).split()
            return StoreViewBox(
                x=float(parts[0]),
                y=float(parts[1]),
                width=float(parts[2]),
                height=float(parts[3])
            )
        return StoreViewBox(0, 0, 100, 100)
    
    def _extract_aisle_labels(self, svg_content: str) -> Dict[str, Tuple[float, float]]:
        """Extract aisle marker positions from SVG text elements."""
        labels = {}
        
        # Match text elements with aisle-like labels (including G##, A##, etc.)
        text_pattern = r'<text[^>]*x="([\d.-]+)"[^>]*y="([\d.-]+)"[^>]*>([A-Z]{1,2}\d{1,3})</text>'
        
        for match in re.finditer(text_pattern, svg_content):
            x = float(match.group(1))
            y = float(match.group(2))
            label = match.group(3)
            
            if label not in labels:
                labels[label] = (x, y)
        
        return labels
    
    def _extract_special_locations(self, svg_content: str) -> Dict[str, Tuple[float, float]]:
        """Extract entrance, checkout locations from SVG labels."""
        locations = {}
        
        patterns = [
            (r'<text[^>]*x="([\d.-]+)"[^>]*y="([\d.-]+)"[^>]*>entrance</text>', 'entrance'),
            (r'<text[^>]*x="([\d.-]+)"[^>]*y="([\d.-]+)"[^>]*>checkout</text>', 'checkout'),
        ]
        
        for pattern, location in patterns:
            for match in re.finditer(pattern, svg_content):
                x = float(match.group(1))
                y = float(match.group(2))
                if location not in locations:
                    locations[location] = (x, y)
        
        return locations
    
    def _parse_path_to_polygon(self, path_d: str) -> List[Tuple[float, float]]:
        """Convert SVG path data to polygon vertices."""
        points = []
        
        # Extract all coordinate pairs from path commands
        coord_pattern = r'[MLCZ]?\s*([\d.-]+)\s+([\d.-]+)'
        
        for match in re.finditer(coord_pattern, path_d):
            try:
                x = float(match.group(1))
                y = float(match.group(2))
                points.append((x, y))
            except ValueError:
                pass
        
        return points
    
    def _extract_paths_by_group(self, svg_content: str, group_id: str) -> List[str]:
        """Extract path data from specific SVG group."""
        paths = []
        
        # Find the group
        group_pattern = rf'<g[^>]*id="{group_id}"[^>]*>(.*?)</g>'
        group_match = re.search(group_pattern, svg_content, re.DOTALL)
        
        if not group_match:
            return paths
        
        group_content = group_match.group(1)
        
        # Extract path elements from group
        path_pattern = r'<path[^>]*d="([^"]+)"'
        for path_match in re.finditer(path_pattern, group_content):
            paths.append(path_match.group(1))
        
        return paths
    
    def _rasterize_polygon(self, grid: np.ndarray, polygon: List[Tuple[float, float]], value: float) -> None:
        """
        Rasterize polygon into grid using scanline algorithm.
        Sets all cells inside polygon to specified value.
        """
        if len(polygon) < 3:
            return
        
        # Convert world coordinates to grid indices
        grid_points = []
        for x, y in polygon:
            gx = int((x - self.viewBox.x) / self.resolution)
            gy = int((y - self.viewBox.y) / self.resolution)
            if 0 <= gx < self.grid_width and 0 <= gy < self.grid_height:
                grid_points.append((gx, gy))
        
        if len(grid_points) < 3:
            return
        
        # Scanline fill
        min_y = min(p[1] for p in grid_points)
        max_y = max(p[1] for p in grid_points)
        
        for row in range(max(0, min_y), min(self.grid_height, max_y + 1)):
            # Find intersections with polygon edges
            intersections = []
            for i in range(len(grid_points)):
                p1 = grid_points[i]
                p2 = grid_points[(i + 1) % len(grid_points)]
                
                if (p1[1] <= row < p2[1]) or (p2[1] <= row < p1[1]):
                    if p2[1] != p1[1]:
                        x_intersect = p1[0] + (row - p1[1]) * (p2[0] - p1[0]) / (p2[1] - p1[1])
                        intersections.append(int(x_intersect))
            
            # Fill between pairs of intersections
            intersections.sort()
            for i in range(0, len(intersections) - 1, 2):
                if i + 1 < len(intersections):
                    x_start = intersections[i]
                    x_end = intersections[i + 1]
                    for col in range(max(0, x_start), min(self.grid_width, x_end + 1)):
                        grid[row, col] = value
    
    def _apply_obstacle_buffer(self, grid: np.ndarray, buffer_cells: int = 2) -> np.ndarray:
        """
        Apply morphological dilation to obstacles.
        Creates safety buffer around aisle shelves and walls.
        """
        from scipy import ndimage
        
        # Binary mask of obstacles (0 = obstacle, 1 = walkable)
        obstacle_mask = (grid < 0.5).astype(np.float32)
        
        # Dilate obstacles using disk structuring element
        # This expands obstacles by buffer_cells in all directions
        structure = ndimage.generate_binary_structure(2, 2)
        dilated = ndimage.binary_dilation(obstacle_mask, structure=structure, iterations=buffer_cells)
        
        # Apply dilated obstacles to grid
        result = grid.copy()
        result[dilated > 0.5] = 0.0
        
        return result
    
    def _apply_corridor_preference(self, grid: np.ndarray, max_boost: float = 0.3) -> np.ndarray:
        """
        Apply distance transform to prefer wider corridors.
        
        Cells in the center of wide walkable areas get a walkability boost,
        encouraging the path to use wider pathways instead of narrow gaps.
        
        Args:
            grid: Walkability grid
            max_boost: Maximum boost to apply (default 0.3)
        
        Returns:
            Grid with corridor preference applied
        """
        from scipy import ndimage
        
        # Binary mask of walkable areas (> 0.5)
        walkable_mask = (grid > 0.5).astype(np.float32)
        
        # Calculate distance to nearest obstacle for each cell
        # Higher values = center of wide corridors
        distance_map = ndimage.distance_transform_edt(walkable_mask)
        
        # Normalize distance map (max distance = ~10-20 cells in typical store)
        max_dist = distance_map.max()
        if max_dist > 0:
            normalized_dist = distance_map / max_dist
        else:
            normalized_dist = distance_map
        
        # Apply boost: cells in center of wide areas get up to max_boost added
        # But cap total walkability at 1.0
        boost = normalized_dist * max_boost
        result = np.clip(grid + boost, 0.0, 1.0)
        
        # Ensure obstacles remain obstacles
        result[grid <= 0.0] = 0.0
        
        return result
    
    def _ensure_access_points(self, grid: np.ndarray) -> None:
        """Ensure entrance and checkout areas are walkable."""
        # Clear small circular area around entrance
        if 'entrance' in self.special_locations:
            ex, ey = self.special_locations['entrance']
            gx = int((ex - self.viewBox.x) / self.resolution)
            gy = int((ey - self.viewBox.y) / self.resolution)
            
            # Clear 3x3 cell area
            for dy in range(-2, 3):
                for dx in range(-2, 3):
                    if 0 <= gy + dy < self.grid_height and 0 <= gx + dx < self.grid_width:
                        grid[gy + dy, gx + dx] = 1.0
        
        # Clear small circular area around checkout
        if 'checkout' in self.special_locations:
            cx, cy = self.special_locations['checkout']
            gx = int((cx - self.viewBox.x) / self.resolution)
            gy = int((cy - self.viewBox.y) / self.resolution)
            
            for dy in range(-2, 3):
                for dx in range(-2, 3):
                    if 0 <= gy + dy < self.grid_height and 0 <= gx + dx < self.grid_width:
                        grid[gy + dy, gx + dx] = 1.0
    
    def _build_walkability_grid(self, svg_content: str) -> np.ndarray:
        """
        Build walkability grid from SVG with gradient walkability levels.
        
        Walkability levels:
        - 1.0: Floor-Pads (light grey) - preferred walking corridors
        - 0.7: Default floor - acceptable (general walking area)
        - 0.3: Register-Shapes (dark grey) - avoid unless necessary (checkout lanes)
        - 0.0: Aisle-Shapes - obstacles (merchandise aisles)
        
        Note: Wall-Shapes are NOT marked as obstacles since they define the store
        perimeter and the path won't go there anyway. This prevents over-constraining.
        
        Process:
        1. Create grid with default walkability (0.7)
        2. Rasterize Floor-Pads as preferred (1.0)
        3. Rasterize Aisle-Shapes as obstacles (0.0)
        4. Rasterize Register-Shapes as low-preference (0.3)
        5. Apply light safety buffer around aisles only
        6. Ensure access points are clear
        """
        # Calculate grid dimensions
        width_cells = int(self.viewBox.width / self.resolution) + 1
        height_cells = int(self.viewBox.height / self.resolution) + 1
        
        # Step 1: Create grid with default walkability (general floor area)
        grid = np.full((height_cells, width_cells), 0.7, dtype=np.float32)
        
        # Step 2: Rasterize Floor-Pads as preferred walking areas (light grey)
        floor_paths = self._extract_paths_by_group(svg_content, 'Floor-Pads')
        for path_d in floor_paths:
            polygon = self._parse_path_to_polygon(path_d)
            if polygon:
                self._rasterize_polygon(grid, polygon, value=1.0)
        
        # Step 3: Rasterize Aisle-Shapes as obstacles (0.0) - merchandise aisles
        aisle_paths = self._extract_paths_by_group(svg_content, 'Aisle-Shapes')
        for path_d in aisle_paths:
            polygon = self._parse_path_to_polygon(path_d)
            if polygon:
                self._rasterize_polygon(grid, polygon, value=0.0)
        
        # Step 4: Rasterize Register-Shapes as low-preference (dark grey checkout lanes)
        # Path will avoid these unless necessary (e.g., to reach checkout)
        register_paths = self._extract_paths_by_group(svg_content, 'Register-Shapes')
        for path_d in register_paths:
            polygon = self._parse_path_to_polygon(path_d)
            if polygon:
                self._rasterize_polygon(grid, polygon, value=0.3)
        
        # Note: Wall-Shapes are NOT marked as obstacles - they're the store perimeter
        # and marking them would create a black border around the entire store
        
        # Step 5: Apply light safety buffer around aisles only (1 cell)
        # This prevents the path from hugging too close to aisle shelves
        grid = self._apply_obstacle_buffer(grid, buffer_cells=1)
        
        # Step 5b: Boost walkability for cells in center of wide corridors
        # Uses distance transform to prefer wider pathways
        grid = self._apply_corridor_preference(grid, max_boost=0.3)
        
        # Step 6: Ensure entrance/checkout are walkable (set to 1.0)
        self._ensure_access_points(grid)
        
        # Calculate statistics
        total_cells = width_cells * height_cells
        preferred = (grid >= 1.0).sum()
        acceptable = ((grid >= 0.7) & (grid < 1.0)).sum()
        avoid = ((grid > 0.0) & (grid < 0.7)).sum()
        obstacle = (grid <= 0.0).sum()
        
        print(f"Grid built: {width_cells}x{height_cells} cells ({total_cells / 1e6:.2f}M cells)")
        print(f"  Preferred (Floor-Pads): {preferred} cells ({preferred/total_cells*100:.1f}%)")
        print(f"  Acceptable (open floor): {acceptable} cells ({acceptable/total_cells*100:.1f}%)")
        print(f"  Avoid (Registers/Checkout zone): {avoid} cells ({avoid/total_cells*100:.1f}%)")
        print(f"  Obstacles (Aisles): {obstacle} cells ({obstacle/total_cells*100:.1f}%)")
        print(f"  Walkable (>0): {(grid > 0).sum()} cells ({(grid > 0).sum() / total_cells * 100:.1f}%)")
        
        return grid
    
    def world_to_grid(self, world_pos: Tuple[float, float]) -> Tuple[int, int]:
        """Convert world coordinates to grid cell indices."""
        x, y = world_pos
        gx = int((x - self.viewBox.x) / self.resolution)
        gy = int((y - self.viewBox.y) / self.resolution)
        return (gy, gx)  # Note: (row, col) order
    
    def grid_to_world(self, grid_cell: Tuple[int, int]) -> Tuple[float, float]:
        """Convert grid cell indices to world coordinates."""
        gy, gx = grid_cell
        x = self.viewBox.x + gx * self.resolution
        y = self.viewBox.y + gy * self.resolution
        return (x, y)
    
    def is_walkable(self, grid_cell: Tuple[int, int]) -> bool:
        """Check if grid cell is walkable."""
        gy, gx = grid_cell
        if 0 <= gy < self.grid_height and 0 <= gx < self.grid_width:
            return self.grid[gy, gx] > 0.5
        return False
    
    def get_walkable_cells(self) -> List[Tuple[int, int]]:
        """Get list of all walkable cell indices."""
        return list(zip(*np.where(self.grid > 0.5)))
    
    def to_debug_svg(self, path: List[Tuple[float, float]] = None) -> str:
        """Generate debug SVG showing walkability grid."""
        from .maze_visualizer import create_maze_debug_svg
        return create_maze_debug_svg(self, path)


def analyze_store(svg_path: str) -> StoreMaze:
    """Load SVG and create maze representation."""
    with open(svg_path, 'r') as f:
        svg_content = f.read()
    
    return StoreMaze(svg_content)


if __name__ == '__main__':
    import sys
    
    svg_path = sys.argv[1] if len(sys.argv) > 1 else '/Users/joelvzach/Code/applsoftcomp-sprint-m03/project/output/store_map_2357_tulsa.svg'
    
    print(f"Analyzing: {svg_path}")
    maze = analyze_store(svg_path)
    
    print(f"\nViewBox: ({maze.viewBox.x:.2f}, {maze.viewBox.y:.2f}) {maze.viewBox.width:.2f}x{maze.viewBox.height:.2f}")
    print(f"Aisle labels found: {len(maze.aisle_labels)}")
    print(f"Special locations: {list(maze.special_locations.keys())}")
    
    if maze.aisle_labels:
        print("\nSample aisle positions:")
        for label, pos in list(maze.aisle_labels.items())[:5]:
            print(f"  {label}: ({pos[0]:.2f}, {pos[1]:.2f})")
