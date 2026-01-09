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


## Licensing & Authorship

This project is licensed under the MIT License.

**Author:** []  
**Institution:** [Your Institution]

If you use this tool in your research, please cite the paper listed below.
