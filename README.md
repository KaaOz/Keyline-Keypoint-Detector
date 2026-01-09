# Keyline Keypoint Detector for QGIS

This repository contains an automated QGIS workflow for identifying hydrological **Keypoints** (valley heads) using the **Geomorphon** landform classification method. This tool translates P.A. Yeomans' Keyline planning principles into a reproducible digital terrain analysis algorithm.

## Features

* **Automated Detection:** Identifies convex-to-concave inflection zones (Hollows) from raw DEMs.
* **Adaptive Analysis:** Uses SAGA Geomorphons for scale-adaptive landform recognition.
* **Classification:** Automatically classifies keypoints into Primary, Secondary, Tertiary, and Quaternary tiers.
* **Hydraulic Context:** Calculates elevation statistics (Min, Max, Mean) to support future gravity-fed network design.

## Installation

### Processing Script

1. Download `keypoint_detector.py`.
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
* **Geomorphon Raster:** Right-click the geomorphon layer > Properties > Symbology > Style > Load Style... > Select geomorphons.qml.
* **Keypoints Layer:** Right-click the point layer > Properties > Symbology > Style > Load Style... > Select keypoint_styles.qml. This will automatically color-code points by their tier (Primary, Secondary, etc.).

## Licensing & Authorship

This project is licensed under the MIT License.

**Author:** []  
**Institution:** [Your Institution]

If you use this tool in your research, please cite the paper listed below.
