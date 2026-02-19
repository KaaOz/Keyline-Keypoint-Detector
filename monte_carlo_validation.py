import random
import math
import os
from qgis.core import (QgsProject, QgsVectorLayer, 
                       QgsSpatialIndex, QgsPointXY,
                       QgsFeature, QgsGeometry, QgsWkbTypes)

# ============================================================
# CONFIGURATION - Modify these values to adapt script to your data
# ============================================================
CATCHMENT_LAYER_NAME  = "sandy_boundary"           
RESERVOIRS_LAYER_NAME = "potable_water_sandy_cr_catch" 
KEYPOINTS_PATH = r"C:\MCP_Folder\claude\DLA2026\files2\Keypoints_Small_500.shp"

# TEST: "MEDIAN Match" Distance
# We calculate the distance to the nearest keypoint for EACH reservoir.
# We then take the MEDIAN of those 5 values.
# This filters out the single "worst" miss (outlier) caused by edge effects.
NUM_ITERATIONS = 1000

# FILTER: Keep this low or 0 since we know they are on the boundary.
# The Median test handles the outlier better than filtering does.
BOUNDARY_EXCLUSION_DIST = 0.0 
# ============================================================

project = QgsProject.instance()

def load_or_get_layer(identifier, is_path=False):
    if not is_path:
        layers = project.mapLayersByName(identifier)
        if layers: return layers[0]
    
    search_path = identifier
    if not is_path:
        print(f"ERROR: Could not find layer named '{identifier}'")
        return None
        
    if os.path.exists(search_path):
        layer_name = os.path.basename(search_path).split('.')[0]
        new_layer = QgsVectorLayer(search_path, layer_name, "ogr")
        return new_layer if new_layer.isValid() else None
    return None

# --- Main Execution ---

print("--- Initializing Layers ---")
catchment_layer = load_or_get_layer(CATCHMENT_LAYER_NAME, is_path=False)
reservoir_layer = load_or_get_layer(RESERVOIRS_LAYER_NAME, is_path=False)
keypoints_layer = load_or_get_layer(KEYPOINTS_PATH, is_path=True)

if not all([catchment_layer, reservoir_layer, keypoints_layer]):
    print("\nSTOPPING: Layers not loaded.")
else:
    print("Layers loaded. Starting 'Median Match Distance' Analysis...")

    # 1. Geometry Prep
    catchment_feat = next(catchment_layer.getFeatures())
    catchment_geom = catchment_feat.geometry()
    
    # FIX: Convert polygon to line to get the boundary edge safely
    catchment_boundary = QgsGeometry(catchment_geom)
    catchment_boundary.convertToType(QgsWkbTypes.LineGeometry)
    
    bbox = catchment_geom.boundingBox()
    x_min, x_max = bbox.xMinimum(), bbox.xMaximum()
    y_min, y_max = bbox.yMinimum(), bbox.yMaximum()

    # 2. Filter Reservoirs by Boundary Distance
    # (Kept for diagnostics, but exclusion is controlled by config)
    all_reservoir_feats = [f for f in reservoir_layer.getFeatures()]
    valid_reservoir_geoms = []
    
    print("\n" + "="*55)
    print("DIAGNOSTICS: Boundary Distance Check")
    for i, feat in enumerate(all_reservoir_feats):
        res_geom = feat.geometry()
        dist_to_edge = res_geom.distance(catchment_boundary)
        
        if dist_to_edge < BOUNDARY_EXCLUSION_DIST:
            print(f"Reservoir {i+1}: {dist_to_edge:.2f} m (Excluded)")
        else:
            valid_reservoir_geoms.append(res_geom)
            # print(f"Reservoir {i+1}: {dist_to_edge:.2f} m (Included)")
            
    # Fallback if config is 0.0 or filter kills everything
    if len(valid_reservoir_geoms) == 0:
        valid_reservoir_geoms = [f.geometry() for f in all_reservoir_feats]
        print("Using ALL reservoirs (Median test is robust to edge outliers).")
    
    print("-" * 55)

    # Get Keypoints coordinates
    actual_points = []
    for feat in keypoints_layer.getFeatures():
        pt = feat.geometry().asPoint()
        actual_points.append((pt.x(), pt.y()))
    
    num_keypoints = len(actual_points)

    # 3. Function: Calculate MEDIAN Distance of Nearest Matches
    def calculate_median_match_distance(points_list, targets):
        distances = []
        for target in targets:
            min_dist = float('inf')
            for x, y in points_list:
                pt_geom = QgsGeometry.fromPointXY(QgsPointXY(x, y))
                dist = target.distance(pt_geom)
                if dist < min_dist:
                    min_dist = dist
            distances.append(min_dist)
        
        if not distances: return 0
        
        # Sort and pick the middle value (Median)
        distances.sort()
        mid_idx = len(distances) // 2
        
        # Simple median (if even, take lower or average, standard is robust enough here)
        return distances[mid_idx]

    # 4. Calculate Actual Statistic
    actual_median_dist = calculate_median_match_distance(actual_points, valid_reservoir_geoms)
    print(f"ACTUAL Median Match Distance: {actual_median_dist:.2f} m")
    print("="*55)

    # 5. Monte Carlo Simulation
    print(f"Running {NUM_ITERATIONS} iterations...")
    random_median_dists = []

    for i in range(NUM_ITERATIONS):
        random_pts = []
        attempts = 0
        while len(random_pts) < num_keypoints:
            rx = random.uniform(x_min, x_max)
            ry = random.uniform(y_min, y_max)
            pt_geom = QgsGeometry.fromPointXY(QgsPointXY(rx, ry))
            
            if catchment_geom.contains(pt_geom):
                random_pts.append((rx, ry))
            attempts += 1
            if attempts > num_keypoints * 200: break 
        
        # Calculate statistic for this random set
        r_median = calculate_median_match_distance(random_pts, valid_reservoir_geoms)
        random_median_dists.append(r_median)
        
        if (i + 1) % 100 == 0: print(f" {i + 1}...")

    # 6. Statistics
    # P-value: Fraction of random trials where the Median Distance was SMALLER (better) than actual
    better_runs = sum(1 for d in random_median_dists if d <= actual_median_dist)
    p_value = better_runs / NUM_ITERATIONS
    
    avg_random_median = sum(random_median_dists) / NUM_ITERATIONS

    # 7. Final Output
    print("\n" + "="*55)
    print("MONTE CARLO RESULTS (MEDIAN DISTANCE)")
    print("="*55)
    print(f"Reservoirs Included:         {len(valid_reservoir_geoms)}")
    print(f"Actual Median Distance:      {actual_median_dist:.2f} m")
    print(f"Random Median Avg:           {avg_random_median:.2f} m")
    print(f"P-value:                     {p_value:.4f}")
    print("-" * 55)
    
    if p_value < 0.05:
        print("RESULT: SIGNIFICANT (p < 0.05)")
        print(f"The 'typical' reservoir (median case) is significantly closer")
        print("to a keypoint than random chance.")
    else:
        print("RESULT: NOT SIGNIFICANT")
    print("="*55)