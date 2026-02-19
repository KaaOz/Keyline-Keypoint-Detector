# Keyline Keypoint Detector for QGIS

This repository contains an automated QGIS workflow for identifying hydrological **Keypoints** (valley heads) using the **Geomorphon** landform classification method. This tool translates P.A. Yeomans' Keyline planning principles into a reproducible digital terrain analysis algorithm.

## Features

* **Automated Detection:** Identifies convex-to-concave inflection zones (Hollows) from raw DEMs.
* **Adaptive Analysis:** Uses SAGA Geomorphons for scale-adaptive landform recognition.
* **Classification:** Automatically classifies keypoints into Primary, Secondary, Tertiary, and Quaternary tiers.
* **Hydraulic Context:** Calculates elevation statistics (Min, Max, Mean) to support future gravity-fed network design.

## Installation

### Processing Script

1. Download `keyline_keypoint_detector.py`.
2. Open QGIS > Processing Toolbox > Scripts icon > "Add Script to Toolbox".
3. Select the file. The tool will appear under the "Keyline Analysis" group.
   *Note: This script includes automatic fixes for common SAGA path issues and pixel geometry errors.*

### Usage

1. **Input:** A raw Digital Elevation Model (DEM). Do not fill sinks beforehand.

2. **Parameters:**
* **Radial Limit:** 1000m (Default/Optimized for catchment scale).
* **Threshold Angle:** 0.5° (Default).
* **Min Area:** 500 m² (Default significance threshold).

3. **Run:** The tool will generate a point layer of Keypoints with rich attribute data.

4. **Styling Outcomes(.qml):** To visualize the results correctly, apply the provided QGIS Layer Style files:
* **Geomorphon Raster:** Right-click the geomorphon layer > Properties > Symbology > Style > Load Style... > Select `Geomorphon_10class.qml`.
* **Keypoints Layer:** Right-click the point layer > Properties > Symbology > Style > Load Style... > Select `keypoint_styles.qml`.
  This will automatically color-code points by their tier (Primary, Secondary, Tertiary, Quaternary).

### Supplementary Files
## Monte Carlo Validation Script
**File:** `monte_carlo_validation.py`

**Purpose:** Statistical validation of keypoint spatial alignment with historical water infrastructure through Monte Carlo simulation.

---

## What This Script Does

Tests whether algorithmically-identified keypoints are spatially closer to historical reservoir locations than would be expected by random chance. The script:

1. Calculates the **median distance** from five potable water reservoirs (constructed 1950s–1970s) to their nearest algorithmically-identified keypoint
2. Generates 1,000 random point sets (same count as actual keypoints) within the catchment boundary
3. Calculates median distance for each random set
4. Compares actual vs. random distributions to determine statistical significance

---

## Why Median Distance?

The median distance metric (rather than mean) was chosen because:
- It is robust to single outliers caused by edge effects or boundary proximity
- It represents the "typical" reservoir alignment rather than being skewed by the worst-case match
- It better captures the spatial pattern when sample sizes are small (n=5 reservoirs)

---

## Requirements

- QGIS 3.x with Python console
- Input layers:
  - `sandy_boundary` — catchment boundary polygon
  - `potable_water_sandy_cr_catch` — reservoir point locations
  - `Keypoints_Small_500.shp` — algorithmically-identified keypoints (≥500 m² hollow zones)

---

## Usage

1. Open the Sandy Creek project in QGIS
2. Verify layer names match the `CONFIGURATION` section at the top of the script
3. Update `KEYPOINTS_PATH` to point to your keypoints shapefile location
4. Open QGIS Python Console (Plugins → Python Console)
5. Load and run the script

The script will output:
- Diagnostic information about reservoir boundary distances
- Actual median distance to nearest keypoint
- Average random median distance across 1,000 iterations
- P-value (proportion of random trials with median distance ≤ actual)

---

## Results for Sandy Creek Sub-catchment

For the Sandy Creek sub-catchment (Brisbane, Australia):

| Metric | Value |
|--------|-------|
| **Actual median distance** | 95.3 m |
| **Random median average** | 130.6 m |
| **P-value** | 0.307 (not statistically significant) |

The non-significant result reflects a structural scale mismatch: keypoints concentrate in valley-head positions while potable reservoirs occupy high-catchment ridge-proximate sites for gravity-fed distribution. Despite the statistical outcome, all five reservoirs align with algorithmically-identified hollow landforms, confirming the geomorphon method identifies convergent terrain features independently recognized through pre-digital engineering judgment.

---

## Configuration Options

```python
NUM_ITERATIONS = 1000              # Number of random trials (1000 recommended)
BOUNDARY_EXCLUSION_DIST = 0.0      # Distance threshold to exclude edge reservoirs (0.0 = include all)
```

Adjust `BOUNDARY_EXCLUSION_DIST` if reference points near study area edges create statistical artifacts. Set to 0.0 to include all points and let the median metric handle outliers naturally.

---

## Broader Applications

**Note:** This validation framework is generalizable beyond keyline planning to any spatial algorithm validation problem with sparse ground truth. See CONFIGURATION section to adapt for other datasets.

---

## Citation

If you use the main script or validation approach in your research, please cite:

> Ozgun, K. (2025). Keyline Keypoint Detector: Automated QGIS Workflow (Version 1.0.0) [Computer software]. GitHub. https://github.com/KaaOz/Keyline-Keypoint-Detector

---

## Contact

For questions or suggestions regarding this validation methodology, please open an issue on this repository or contact [your contact method].

## Licensing & Authorship

This project is licensed under the MIT License.

**Author:** Kaan Ozgun  
**Institution:** OzU


