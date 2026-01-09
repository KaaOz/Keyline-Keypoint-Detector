from qgis.core import (QgsProcessing,
                       QgsProcessingAlgorithm,
                       QgsProcessingParameterRasterLayer,
                       QgsProcessingParameterNumber,
                       QgsProcessingParameterFeatureSink,
                       QgsProcessingException,
                       QgsApplication,
                       QgsUnitTypes,
                       QgsProject,
                       QgsRasterLayer)
import processing
import os
import tempfile
import shutil
import time

class KeylineKeypointDetector(QgsProcessingAlgorithm):
    """
    Automated Keyline Keypoint Detection Algorithm
    Translates Yeomans' keypoint concept into a geomorphon-based workflow.
    Includes invisible hydraulic attribute enrichment (Z-stats) for future network modeling.
    """

    # Constants for input parameters
    INPUT_DEM = 'INPUT_DEM'
    RADIAL_LIMIT = 'RADIAL_LIMIT'
    THRESHOLD_ANGLE = 'THRESHOLD_ANGLE'
    MIN_AREA = 'MIN_AREA'
    OUTPUT = 'OUTPUT'

    def tr(self, string):
        return string

    def createInstance(self):
        return KeylineKeypointDetector()

    def name(self):
        return 'keypointdetector'

    def displayName(self):
        return self.tr('Keyline Keypoint Detector')

    def group(self):
        return self.tr('Keyline Analysis')

    def groupId(self):
        return 'keylineanalysis'

    def shortHelpString(self):
        return self.tr("Identifies hydrologically significant 'Keypoints' (valley heads) using Geomorphon landform classification. \n\n"
                       "<b>CRITICAL REQUIREMENTS:</b>\n"
                       "- <b>Projected CRS:</b> Input DEM MUST be in meters (e.g., UTM). Lat/Lon (WGS84) will fail area calculations.\n"
                       "- <b>Raw DEM:</b> Do not fill sinks beforehand. The algorithm needs actual morphology.\n\n"
                       "<b>Resolution Notes:</b>\n"
                       "- <b>1m:</b> Supported but very slow. Tool may look like it freezes. Be patient.\n"
                       "- <b>30m:</b> Supported but may be too coarse to find small keypoints.\n"
                       "- <b>5m:</b> Recommended balance.\n\n"
                       "Reference: Yeomans' Keyline Plan (1954) adapted via Geomorphons (Jasiewicz & Stepinski, 2013).")

    def initAlgorithm(self, config=None):
        # 1. Input DEM
        self.addParameter(
            QgsProcessingParameterRasterLayer(
                self.INPUT_DEM,
                self.tr('Input DEM (Raw/Unfilled, Projected CRS)')
            )
        )

        # 2. Radial Limit (Default: 1000m based on paper optimization)
        param_rl = QgsProcessingParameterNumber(
            self.RADIAL_LIMIT, 
            self.tr('Radial Limit (meters)'),
            type=QgsProcessingParameterNumber.Integer,
            defaultValue=1000,
            minValue=100,
            maxValue=10000
        )
        self.addParameter(param_rl)

        # 3. Threshold Angle (Default: 0.5 degrees)
        param_ta = QgsProcessingParameterNumber(
            self.THRESHOLD_ANGLE,
            self.tr('Threshold Angle (degrees)'),
            type=QgsProcessingParameterNumber.Double,
            defaultValue=0.5,
            minValue=0.0,
            maxValue=10.0
        )
        self.addParameter(param_ta)

        # 4. Minimum Area Threshold (Default: 500m2)
        param_area = QgsProcessingParameterNumber(
            self.MIN_AREA,
            self.tr('Minimum Hollow Area (m²)'),
            type=QgsProcessingParameterNumber.Double,
            defaultValue=500,
            minValue=0
        )
        self.addParameter(param_area)

        # 5. Output Layer
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT,
                self.tr('Identified Keypoints')
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        feedback.pushInfo("Script Version: FINAL FIXED (Square Pixels + Direct Paths + Auto-Load Geomorphons)")
        
        source_dem_layer = self.parameterAsRasterLayer(parameters, self.INPUT_DEM, context)
        radial_limit = self.parameterAsInt(parameters, self.RADIAL_LIMIT, context)
        threshold_angle = self.parameterAsDouble(parameters, self.THRESHOLD_ANGLE, context)
        min_area = self.parameterAsDouble(parameters, self.MIN_AREA, context)

        # --- 1. Validation Checks ---
        if not source_dem_layer:
            raise QgsProcessingException("Invalid DEM layer provided.")

        crs = source_dem_layer.crs()
        if crs.isGeographic():
            raise QgsProcessingException("ERROR: Input DEM is in a Geographic CRS (Lat/Lon). You MUST reproject it to a Projected CRS (e.g., UTM or local grid in meters) before running this tool.")

        # Resolution & Unit Check
        units = crs.mapUnits()
        if units != QgsUnitTypes.DistanceMeters:
             feedback.pushInfo(f"WARNING: CRS units are not meters ({QgsUnitTypes.toString(units)}). Parameters are assumed to be in map units.")

        pixel_size = source_dem_layer.rasterUnitsPerPixelX()
        feedback.pushInfo(f"Detected pixel size: {pixel_size:.6f} map units")
        
        if pixel_size < 2.0:
            feedback.pushInfo("NOTICE: High resolution DEM (< 2m) detected. SAGA processing may be slow and appear to freeze. This is normal.")
        elif pixel_size > 20.0:
            feedback.pushInfo("NOTICE: Coarse resolution DEM (> 20m) detected. Keypoints may be generalized.")

        # --- 2. Safe Temporary Folder Setup (Critical for SAGA) ---
        safe_base = "C:/Temp"
        if not os.path.exists(safe_base):
            try:
                os.makedirs(safe_base)
            except:
                safe_base = tempfile.gettempdir()
        
        # Unique folder for this run
        run_id = time.strftime("%Y%m%d_%H%M%S")
        temp_dir = os.path.join(safe_base, f"keyline_{run_id}")
        os.makedirs(temp_dir, exist_ok=True)
        feedback.pushInfo(f"Processing in safe directory: {temp_dir}")

        # Overwrite Environment Variables to force SAGA to use our safe dir
        os.environ['TMP'] = temp_dir
        os.environ['TEMP'] = temp_dir

        # Define explicit intermediate paths
        path_saga_dem = os.path.join(temp_dir, "input_dem.sdat") 
        path_geomorphs = os.path.join(temp_dir, "01_geomorphons.sdat")
        path_hollows_ras = os.path.join(temp_dir, "02_hollows.tif")
        path_hollows_vec = os.path.join(temp_dir, "03_hollows_raw.gpkg")
        path_hollows_fix = os.path.join(temp_dir, "04_hollows_fixed.gpkg")
        path_hollows_z = os.path.join(temp_dir, "05_hollows_z.gpkg")
        path_hollows_area = os.path.join(temp_dir, "06_hollows_area.gpkg")
        path_filtered = os.path.join(temp_dir, "07_filtered.gpkg")
        path_classified = os.path.join(temp_dir, "08_classified.gpkg")
        
        # --- 3. SANITIZE INPUT & CONVERT TO SAGA FORMAT ---
        feedback.pushInfo(f"Converting input DEM to SAGA format (forcing square pixels): {path_saga_dem}...")
        
        # Determine strict pixel size to avoid SAGA 'rect grids only' error
        res_val = float(f"{pixel_size:.6f}") # Round to 6 decimals
        
        # Use gdal:warpreproject instead of translate. 
        # Warp is robust for regridding and enforcing square pixels.
        processing.run("gdal:warpreproject", {
            'INPUT': source_dem_layer,
            'SOURCE_CRS': crs,
            'TARGET_CRS': crs,
            'RESAMPLING': 1, # Bilinear
            'NODATA': -9999,
            'TARGET_RESOLUTION': res_val, # Force X=Y resolution
            'OPTIONS': '',
            'DATA_TYPE': 0, 
            'TARGET_EXTENT': None,
            'TARGET_EXTENT_CRS': None,
            'MULTITHREADING': False,
            'OUTPUT': path_saga_dem # SAGA format
        }, context=context, feedback=feedback, is_child_algorithm=True)

        if not os.path.exists(path_saga_dem):
             raise QgsProcessingException("Failed to create safe SAGA copy of Input DEM. Check permissions.")

        # --- Step 1: SAGA Geomorphons ---
        feedback.pushInfo('Step 1/7: Running Geomorphon Classification...')
        
        saga_target = path_geomorphs

        # DYNAMIC ALGORITHM DETECTION
        saga_candidates = [
            ('sagang:geomorphons', 'DEM'), 
            ('sagang:geomorphons', 'GRID'), 
            ('sagang:geomorphons', 'ELEVATION'),
            ('saga:geomorphons', 'DEM'),
            ('saga:geomorphons', 'GRID'),
            ('saga:geomorphons', 'ELEVATION')
        ]
        
        success = False
        last_error = None
        attempted_algs = []

        for alg_id, input_param in saga_candidates:
            if QgsApplication.processingRegistry().algorithmById(alg_id) is None:
                continue

            try:
                feedback.pushInfo(f"Attempting to run {alg_id} using param '{input_param}'...")
                attempted_algs.append(f"{alg_id} ({input_param})")
                
                params = {
                    input_param: path_saga_dem, 
                    'RADIUS': radial_limit,
                    'THRESHOLD': threshold_angle,
                    'METHOD': 1, 
                    'GEOMORPHONS': saga_target
                }
                
                processing.run(alg_id, params, context=context, feedback=feedback, is_child_algorithm=True)
                
                if os.path.exists(saga_target) or os.path.exists(saga_target.replace('.sdat', '.sgrd')):
                    success = True
                    feedback.pushInfo(f"Success with {alg_id}!")
                    break
            except Exception as e:
                last_error = f"{alg_id} ({input_param}): {e}"
                continue

        if not success:
             algs = QgsApplication.processingRegistry().algorithms()
             geo_algs = [a.id() for a in algs if 'geomorphon' in a.id().lower()]
             feedback.reportError(f"Found these Geomorphon algorithms on your system: {geo_algs}")
             raise QgsProcessingException(f"Critical Error: Could not find or run SAGA Geomorphons.\nTried: {attempted_algs}.\nLast Error: {last_error}")

        # --- Step 2: Reclassify (Isolate Hollows) ---
        feedback.pushInfo('Step 2/7: Isolating Hollow Zones...')
        processing.run("native:reclassifybytable", {
            'INPUT_RASTER': saga_target, 
            'RASTER_BAND': 1,
            'TABLE': [6.5, 7.5, 1], 
            'NO_DATA': -9999,
            'RANGE_BOUNDARIES': 0, 
            'NODATA_FOR_MISSING': True,
            'DATA_TYPE': 2, # Int16
            'OUTPUT': path_hollows_ras 
        }, context=context, feedback=feedback, is_child_algorithm=True)

        # --- Step 3: Polygonize ---
        feedback.pushInfo('Step 3/7: Converting to Vectors...')
        processing.run("gdal:polygonize", {
            'INPUT': path_hollows_ras,
            'BAND': 1,
            'FIELD': 'class_id',
            'EIGHT_CONNECTEDNESS': False,
            'OUTPUT': path_hollows_vec
        }, context=context, feedback=feedback, is_child_algorithm=True)

        # --- Step 4: Fix Geometries ---
        feedback.pushInfo('Step 4/7: Repairing Invalid Geometries...')
        processing.run("native:fixgeometries", {
            'INPUT': path_hollows_vec,
            'OUTPUT': path_hollows_fix
        }, context=context, feedback=feedback, is_child_algorithm=True)

        # --- Step 5: Add Z-Statistics ---
        feedback.pushInfo('Step 5/7: Calculating Elevation Statistics...')
        # Use the SAGA-compatible input DEM (safe path) for consistency
        processing.run("native:zonalstatisticsfb", {
            'INPUT': path_hollows_fix,
            'INPUT_RASTER': path_saga_dem, 
            'RASTER_BAND': 1,
            'COLUMN_PREFIX': 'z_',
            'STATISTICS': [2, 5, 6], # Mean, Min, Max
            'OUTPUT': path_hollows_z 
        }, context=context, feedback=feedback, is_child_algorithm=True)

        # --- Step 6: Calculate Area & Filter ---
        feedback.pushInfo('Step 6/7: Filtering by Area...')
        
        # Calculate Area
        processing.run("native:fieldcalculator", {
            'INPUT': path_hollows_z,
            'FIELD_NAME': 'area_m2',
            'FIELD_TYPE': 0, # Float
            'FIELD_LENGTH': 10, 
            'FIELD_PRECISION': 2,
            'FORMULA': 'area($geometry)',
            'OUTPUT': path_hollows_area 
        }, context=context, feedback=feedback, is_child_algorithm=True)

        # Filter 
        expression = f"\"area_m2\" >= {min_area}"
        processing.run("native:extractbyexpression", {
            'INPUT': path_hollows_area,
            'EXPRESSION': expression,
            'OUTPUT': path_filtered 
        }, context=context, feedback=feedback, is_child_algorithm=True)

        # --- Step 7: Classification & Centroids ---
        feedback.pushInfo('Step 7/7: Finalizing Keypoints...')
        
        type_formula = """
        CASE 
        WHEN "area_m2" > 10000 THEN 'Primary' 
        WHEN "area_m2" >= 5000 AND "area_m2" <= 10000 THEN 'Secondary' 
        WHEN "area_m2" >= 1000 AND "area_m2" < 5000 THEN 'Tertiary' 
        ELSE 'Quaternary' 
        END
        """
        # We classify
        # Using explicit string path for INPUT to avoid TypeError
        processing.run("native:fieldcalculator", {
            'INPUT': path_filtered,
            'FIELD_NAME': 'keypoint_type',
            'FIELD_TYPE': 2, 
            'FIELD_LENGTH': 20, 
            'FIELD_PRECISION': 0,
            'FORMULA': type_formula,
            'OUTPUT': path_classified 
        }, context=context, feedback=feedback, is_child_algorithm=True)
        
        # Final Output - Centroids
        processing.run("native:centroids", {
            'INPUT': path_classified,
            'ALL_PARTS': False,
            'OUTPUT': parameters[self.OUTPUT]
        }, context=context, feedback=feedback, is_child_algorithm=True)

        # --- User Feedback & Post-Processing ---
        feedback.pushInfo("\n" + "="*40)
        feedback.pushInfo("SUCCESS! Keypoints Generated.")
        feedback.pushInfo("="*40)
        feedback.pushInfo(f"Intermediate files location:\n{temp_dir}")
        feedback.pushInfo("\nDrag-and-drop to QGIS:")
        feedback.pushInfo(f"- Geomorphons: {path_geomorphs}")
        feedback.pushInfo(f"- Hollows: {path_classified}")
        feedback.pushInfo("="*40 + "\n")

        # AUTO-LOAD GEOMORPHONS LOGIC
        # 1. Load the layer
        if os.path.exists(path_geomorphs):
            # Create raster layer instance
            geo_layer = QgsRasterLayer(path_geomorphs, "Geomorphons (Landforms)")
            if geo_layer.isValid():
                # 2. Apply QML Style (if found next to this script)
                # Note: 'os.path.dirname(__file__)' might fail in some contexts, so we try basic paths
                script_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else ""
                # Try common names: geomorphons.qml, style.qml
                qml_path = os.path.join(script_dir, "geomorphons.qml")
                
                if not os.path.exists(qml_path):
                    # Fallback: check C:/Temp or user might put it in their project folder
                    # For now, just log that we looked
                    feedback.pushInfo(f"Note: No 'geomorphons.qml' found at {qml_path}. Layer loaded with default style.")
                else:
                    geo_layer.loadNamedStyle(qml_path)
                    feedback.pushInfo(f"Applied style from {qml_path}")

                # Add to project
                QgsProject.instance().addMapLayer(geo_layer)
                feedback.pushInfo("Loaded Geomorphons layer to map canvas.")
            else:
                feedback.reportError("Failed to load Geomorphons layer.")

        return {self.OUTPUT: parameters[self.OUTPUT]}