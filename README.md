# Express KMZ Exporter - FTTH Networks for QGIS

Automation tool for **QGIS** designed to process, validate, transform, and export fiber optic infrastructure (**FTTH**) vector layers to compressed **KMZ** files (compatible with Google Earth, Google Maps, Organic Maps, and mobile GIS viewers).

The script is parameterized using a configurable FTTH network element catalog (`LAYER_CATALOG`).

---

## Table of Contents

- [Key Features](#key-features)
- [Prerequisites](#prerequisites)
- [How to Run the Script in QGIS](#how-to-run-the-script-in-qgis)
- [GUI User Guide](#gui-user-guide)
  - [1. Node Grouping Strategy](#1-node-grouping-strategy)
  - [2. Layer Configuration & Mapping](#2-layer-configuration--mapping)
  - [3. Output Directory & Export](#3-output-directory--export)
- [Technical Element Catalog](#technical-element-catalog)
- [Internal Processing Workflow](#internal-processing-workflow)
- [Validations and Error Handling](#validations-and-error-handling)
- [Resulting KMZ Structure](#resulting-kmz-structure)

---

## Key Features

- **Integrated Graphical Interface (PyQt5):** Interactive dialog to map layers, select attribute fields, and configure nodes.
- **Smart Fuzzy Matching Detection:** Automatically associates loaded layer names with catalog element types, regardless of word order (e.g., `backbone_144` with `BACKBONE 144`).
- **Export Modes:**
  - **Single Node:** Exports all selected layers into a single `.kmz` file.
  - **Multiple Nodes:** Automatically splits and generates independent `.kmz` files based on a node attribute field (e.g., `NODE` field).
- **Automatic Reprojection to WGS84 (`EPSG:4326`):** Transforms any source coordinate system (e.g., POSGAR, Gauss-Krüger, UTM) to the geographic standard required by KML/KMZ.
- **Preconfigured Symbology and Styles:** Applies colors (KML format `aabbggrr`), line widths, and official Google Earth icons for each network element.
- **Exhaustive Data Audit and Validation:** Inspects null/empty geometries and missing attributes before generating files, presenting a unified inconsistency report.

---

## Prerequisites

1. **QGIS 3.x** installed (version 3.16 LTR or higher recommended).
2. QGIS project open with vector layers loaded (Shapefiles, GeoPackage, etc.).
3. Access to the QGIS integrated Python console. No additional external libraries required; the script uses native Python modules (`os`, `zipfile`, `xml.etree.ElementTree`, `difflib`, `re`) and QGIS APIs (`qgis.core`, `qgis.gui`, `qgis.PyQt`).

---

## How to Run the Script in QGIS

The script uses the global `iface` object provided by the QGIS interactive environment, so it **must be executed exclusively from the QGIS Python Console**.

### Step by Step:

1. **Open QGIS** and load the project or vector layers you want to export.
2. **Select layers to export:**
   - In the QGIS **Layers Panel**, hold down `Ctrl` or `Shift` and **select all vector layers** that will be part of the KMZ (closures, LCPs, FATs, backbones, etc.).
   > ⚠️ **Important:** If no vector layer is selected before running the script, a warning message will appear and the process will be canceled.
3. **Open the Python Console:**
   - Go to the top menu: **Plugins** -> **Python Console**, or press the keyboard shortcut `Ctrl + Alt + P`.
4. **Open the Code Editor:**
   - In the Python console toolbar, click the notepad/pencil icon (**Show Editor**).
5. **Load the script:**
   - In the editor, click **Open script...** and navigate to `create_kmz_template.py`.
6. **Run the script:**
   - Click the green **Run script** button or press `F5` with the editor active.
7. The **FTTH KMZ Exporter Setup** popup window will appear.

---

## GUI User Guide

When the script runs, the configuration dialog is presented, divided into three main sections:

```
┌────────────────────────────────────────────────────────────────────────┐
│                      FTTH KMZ Exporter Setup                           │
├────────────────────────────────────────────────────────────────────────┤
│ [1] Node Grouping Strategy                                            │
│   (o) Single Node (One global KMZ file)                                │
│       [ Enter node/folder name (e.g. NODO_CENTRO) ]                    │
│   ( ) Multiple Nodes (Split into multiple KMZ files by field attribute)│
│       [ ComboBox with node attribute fields ]                          │
├────────────────────────────────────────────────────────────────────────┤
│ [2] Layer Configuration Table                                          │
│   Layer Name        | Entity Type Target     | Content Field (Name)    │
│   ------------------+------------------------+---------------------    │
│   CENTROS DE NODO   | CO                     | ID_CO                   │
│   FAT_LAYER         | FAT                    | CODE_FAT                │
│   BACKBONE_144      | BACKBONE 144           | fid                     │
├────────────────────────────────────────────────────────────────────────┤
│ [3] Output Folder & Buttons                                            │
│   [ C:/Output/Path... ]   [ Browse Output Folder... ]                  │
│                                                                        │
│                                      [ Export KMZ ]  [ Cancel / Abort ]│
└────────────────────────────────────────────────────────────────────────┘
```

### 1. Node Grouping Strategy
- **Single Node (One global KMZ file):**
  - Enables unified export into a single `.kmz` file.
  - Enter the name of the node or main folder in the text box (e.g., `NODE 07` or `NODE_SOUTH`).
- **Multiple Nodes (Split into multiple KMZ files by field attribute):**
  - Splits the network into multiple `.kmz` files based on the value of an existing field in the layers (e.g., `NODE`, `SECTOR`, or `ZONE`).
  - Enables the dropdown menu to select the splitting field.

### 2. Layer Configuration Table
The table automatically lists all vector layers selected in QGIS:
- **Layer Name:** Layer name in the layer tree (read-only).
- **Entity Type Target:** Dropdown menu with FTTH catalog types. The script automatically assigns a preliminary match by evaluating the layer name. You can change it manually if you want to reassign a category.
- **Content Field (Name Attribute):** Layer attribute used as the visible name of each element in Google Earth. The script automatically omits irrelevant attributes like `type` and `block_name` and selects the first useful field.

### 3. Output Folder & Export
- Click **Browse Output Folder...** to select the directory where `.kmz` files will be saved.
- Click **Export KMZ** to start validation and generation.
- Click **Cancel / Abort** to close without making changes.

---

## Technical Element Catalog

The `LAYER_CATALOG` dictionary defines the hierarchy, geometry, symbology, and naming rules for each network element:

| Element | Geometry | KML Order | Color (KML Hex) | Size / Width | Style / Icon |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **CO** | Point | 1 | `ff000000` (Black) | 2.4 | Square |
| **Splice Closure** | Point | 2 | `ff631ee9` | 1.2 | Triangle |
| **LCP** | Point | 3 | `ffd4bc00` | 1.2 | Triangle |
| **FAT** | Point | 4 | `ff30b1f3` | 1.2 | Shaded dot |
| **BACKBONE 144** | Line | 5 | `ff0000ff` (Red) | Width: 3.0 | Backbone line |
| **BACKBONE 24** | Line | 9 | `ff00ff00` (Green) | Width: 3.0 | Backbone line |
| **BACKBONE 12** | Line | 10 | `ffff00ff` (Magenta) | Width: 3.0 | Backbone line |
| **LATERAL 12** | Line | 11 | `ffff00ff` (Magenta) | Width: 1.2 | Lateral line |

> **Note on KML Colors:** KML color codes are expressed in hexadecimal in `aabbggrr` format (Alpha, Blue, Green, Red), rather than the standard web `rrggbbaa` order.

---

## Internal Processing Workflow

The main `run()` method orchestrates 4 sequential phases:

```
[Selected Layers in QGIS]
             │
             ▼
 1. _display_configuration_dialog()
    - PyQt GUI
    - Fuzzy type matching
    - User parameters capture
             │
             ▼
 2. _input_check_inputs_validity()
    - Output directory validation
    - Null or empty geometry audit
    - Required attributes verification
             │
             ▼
 3. _process_and_group_features()
    - Reprojection to CRS EPSG:4326 (WGS84)
    - Coordinate formatting for Point / LineString / MultiPolyline
    - Name extraction and grouping by Node and Type
             │
             ▼
 4. _create_and_save_kmz()
    - KML 2.2 XML tree construction
    - Style generation and Placemark insertion
    - Temporary doc.kml creation and ZIP compression to {node}.kmz
    - Cleanup of temporals and success notification
```

---

## Validations and Error Handling

The script does not export corrupted or incomplete data. During the `_input_check_inputs_validity()` phase, it performs the following checks:

1. **Output Directory:** Verifies that the path exists in the file system.
2. **Single Node Name:** Confirms the name field is not empty.
3. **Node Field Existence:** In multi-node mode, validates that the selected attribute exists across all analyzed layers.
4. **Valid Geometry:** Inspects feature by feature (`feature.geometry()`) to ensure no records have null (`isNull()`) or empty (`isEmpty()`) geometries.
5. **Mandatory Content Attributes:** For elements requiring content (`has_content: True`), verifies that no record has `NULL` or empty values.

If inconsistencies are detected:
- The process stops before writing any files.
- Errors are printed in detail in the QGIS Python console.
- An error dialog (`QMessageBox.critical`) displays a list of the first inconsistencies found and their identifier (`FID`), allowing quick location and correction in QGIS.

---

## Resulting KMZ Structure

Each generated `.kmz` file follows a clean, standardized hierarchical structure when opened in Google Earth:

```text
Selected_Node.kmz
└── doc.kml
    └── Document [Node Name]
        └── Root Folder [Node Name]
            ├── CO/                    (Black square icons with IDs)
            ├── Splice Closure/        (Purple triangle icons with IDs)
            ├── LCP/                   (Yellow triangle icons with IDs)
            ├── FAT/                   (Light blue shaded dots with IDs)
            ├── BACKBONE 144/          (Red lines, 3.0 px)
            ├── BACKBONE 24/           (Green lines, 3.0 px)
            ├── BACKBONE 12/           (Magenta lines, 3.0 px)
            └── LATERAL 12/            (Magenta lines, 1.2 px)
```

Compressed in KMZ format, the file is lightweight, self-contained, and ready to be distributed to field technicians or clients.
