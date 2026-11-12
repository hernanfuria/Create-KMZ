import os
import zipfile
import xml.etree.ElementTree as ET
import difflib
import re

from qgis.core import (
    QgsProject,
    Qgis,
    QgsVectorLayer,
    QgsFeature,
    QgsGeometry,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform
)
from qgis.gui import QgisInterface
from qgis.PyQt.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QRadioButton,
    QLineEdit,
    QComboBox,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QLabel,
    QFileDialog,
    QGroupBox,
    QHeaderView,
    QMessageBox
)
from qgis.PyQt.QtCore import Qt

# Catalog containing stylistic metadata and display settings for FTTH entities
LAYER_CATALOG = {
    "CO": {"geom": "Point", "order": 1, "size": 2.4, "color": "ff000000", "icon": "http://maps.google.com/mapfiles/kml/shapes/square.png", "has_content": True},
    "Splice Closure": {"geom": "Point", "order": 2, "size": 1.2, "color": "ff631ee9", "icon": "http://maps.google.com/mapfiles/kml/shapes/triangle.png", "has_content": True},
    "LCP": {"geom": "Point", "order": 3, "size": 1.2, "color": "ffd4bc00", "icon": "http://maps.google.com/mapfiles/kml/shapes/triangle.png", "has_content": True},
    "FAT": {"geom": "Point", "order": 4, "size": 1.2, "color": "ff30b1f3", "icon": "http://maps.google.com/mapfiles/kml/shapes/shaded_dot.png", "has_content": True},
    
    "BACKBONE 144": {"geom": "LineString", "order": 5, "width": 3.0, "color": "ff0000ff", "has_content": True},  # red
    "BACKBONE 24": {"geom": "LineString", "order": 9, "width": 3.0, "color": "ff00ff00", "has_content": True},  # green
    "BACKBONE 12": {"geom": "LineString", "order": 10, "width": 3.0, "color": "ffff00ff", "has_content": True},  # magenta

    "LATERAL 12": {"geom": "LineString", "order": 11, "width": 1.2, "color": "ffff00ff", "has_content": True},  # magenta
}

def normalize_text(text):
    """
    Limpia el texto, separa palabras por caracteres no alfanuméricos
    y las devuelve ordenadas alfabéticamente en minúsculas.
    """
    # Reemplaza guiones bajos o símbolos por espacios y pasa a minúsculas
    words = re.findall(r'\w+', text.lower())
    # Opcional: abreviar 'preconectorizado' a 'preco' si tus SHP suelen usar la palabra larga
    # words = ["preco" if w == "preconectorizado" else w for w in words]
    # Retorna las palabras ordenadas y unidas por un espacio
    return " ".join(sorted(words))


class KMZExporterDialog(QDialog):
    """Unified graphical dialog to configure the KMZ export process."""

    def __init__(self, selected_layers, parent=None):
        super().__init__(parent)
        self.setWindowTitle("FTTH KMZ Exporter Setup")
        self.resize(750, 500)
        self.selected_layers = selected_layers
        self.output_directory = ""
        self.is_single_node = True

        self._build_ui()

    def _build_ui(self):
        """Constructs and arranges GUI components inside the main dialog."""
        layout = QVBoxLayout(self)

        # 1. Grouping Selection Box
        group_box = QGroupBox("Node Grouping Strategy")
        group_layout = QVBoxLayout()

        self.radio_single = QRadioButton("Single Node (One global KMZ file)")
        self.radio_single.setChecked(True)
        self.radio_single.toggled.connect(self._toggle_grouping_mode)

        self.txt_single_node = QLineEdit()
        self.txt_single_node.setPlaceholderText("Enter node/folder name (e.g. NODO_CENTRO)")

        self.radio_multi = QRadioButton("Multiple Nodes (Split into multiple KMZ files by field attribute)")
        self.combo_node_field = QComboBox()
        self.combo_node_field.setEnabled(False)

        # Populate fields available in the first layer for node grouping
        if self.selected_layers:
            fields = [field.name() for field in self.selected_layers[0].fields()]
            self.combo_node_field.addItems(fields)

        group_layout.addWidget(self.radio_single)
        group_layout.addWidget(self.txt_single_node)
        group_layout.addWidget(self.radio_multi)
        group_layout.addWidget(self.combo_node_field)
        group_box.setLayout(group_layout)
        layout.addWidget(group_box)

        # 2. Layer Configuration Table
        self.table = QTableWidget(len(self.selected_layers), 3)
        self.table.setHorizontalHeaderLabels(["Layer Name", "Entity Type Target", "Content Field (Name Attribute)"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        catalog_keys = list(LAYER_CATALOG.keys())

        # Creamos una versión "normalizada" de cada clave del catálogo para comparar
        # Ejemplo: "PRECO 200m" -> "200m preco"
        normalized_catalog = {normalize_text(key): key for key in catalog_keys}
        norm_catalog_keys = list(normalized_catalog.keys())

        for row, layer in enumerate(self.selected_layers):
            # 1. Layer Name (Non-editable)
            item_name = QTableWidgetItem(layer.name())
            item_name.setFlags(item_name.flags() ^ Qt.ItemIsEditable)
            self.table.setItem(row, 0, item_name)

            # 2. Entity Type ComboBox (Fuzzy Match agnóstico al orden)
            combo_type = QComboBox()
            combo_type.addItems(catalog_keys)
            
            # Normalizamos el nombre del SHP actual (Ej: "200m_PRECONECTORIZADO" -> "200m preco")
            norm_layer_name = normalize_text(layer.name())
            
            # Buscamos coincidencias sobre las claves normalizadas
            matches = difflib.get_close_matches(norm_layer_name, norm_catalog_keys, n=1, cutoff=0.3)
            if matches:
                matched_norm_key = matches[0]
                # Recuperamos la clave real del catálogo a partir de la normalizada
                best_match = normalized_catalog[matched_norm_key]
                combo_type.setCurrentIndex(catalog_keys.index(best_match))
                
            self.table.setCellWidget(row, 1, combo_type)

            # 3. Field Selector ComboBox (Ignorar "type" y "block_name")
            combo_field = QComboBox()
            fields = [field.name() for field in layer.fields()]
            combo_field.addItems(fields)
            
            ignored_fields = ["type", "block_name"]
            default_field_index = -1
            for idx, field in enumerate(fields):
                if field.lower() not in ignored_fields:
                    default_field_index = idx
                    break
            for idx, field in enumerate(fields):
                if field.lower() == "attr id":
                    default_field_index = idx
                    break
                    
            if default_field_index != -1:
                combo_field.setCurrentIndex(default_field_index)
                
            self.table.setCellWidget(row, 2, combo_field)

        layout.addWidget(self.table)

        # 3. Output Directory Picker
        path_layout = QHBoxLayout()
        self.txt_output_path = QLineEdit()
        self.txt_output_path.setReadOnly(True)
        btn_browse = QPushButton("Browse Output Folder...")
        btn_browse.clicked.connect(self._select_output_folder)

        path_layout.addWidget(self.txt_output_path)
        path_layout.addWidget(btn_browse)
        layout.addLayout(path_layout)

        # 4. Action Buttons (Run / Abort)
        btn_layout = QHBoxLayout()
        btn_run = QPushButton("Export KMZ")
        btn_run.clicked.connect(self.accept)
        btn_abort = QPushButton("Cancel / Abort")
        btn_abort.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(btn_run)
        btn_layout.addWidget(btn_abort)
        layout.addLayout(btn_layout)

    def _toggle_grouping_mode(self):
        """Switches controls state based on single or multi-node selection."""
        is_single = self.radio_single.isChecked()
        self.is_single_node = is_single
        self.txt_single_node.setEnabled(is_single)
        self.combo_node_field.setEnabled(not is_single)

    def _select_output_folder(self):
        """Prompts the user to pick a target directory."""
        directory = QFileDialog.getExistingDirectory(self, "Select Save Directory")
        if directory:
            self.output_directory = directory
            self.txt_output_path.setText(directory)

    def get_configuration(self):
        """Extracts and returns user configurations upon dialog acceptance."""
        layer_configs = []
        for row in range(self.table.rowCount()):
            layer = self.selected_layers[row]
            combo_type = self.table.cellWidget(row, 1)
            combo_field = self.table.cellWidget(row, 2)

            layer_configs.append({
                "layer": layer,
                "type_key": combo_type.currentText(),
                "content_field": combo_field.currentText()
            })

        return {
            "is_single_node": self.is_single_node,
            "single_node_name": self.txt_single_node.text().strip(),
            "node_field_name": self.combo_node_field.currentText(),
            "output_dir": self.output_directory,
            "layers": layer_configs
        }


class CreateKMZ:
    """Encapsulates the entire workflow to generate structured FTTH KMZ files."""

    def __init__(self, iface: QgisInterface):
        self.iface = iface
        self.CONTINUE = True
        self.config = {}
        self.processed_nodes = {}  # Output structure: { node_name: { type_key: [ {name, coords}, ... ] } }

    def log_message(self, message: str, level=Qgis.Info):
        """Prints log details in console and shows status bar alerts on errors."""
        print(f"[CreateKMZ] {message}")
        if level in [Qgis.Warning, Qgis.Critical]:
            self.iface.messageBar().pushMessage("KMZ Exporter Error", message, level=level, duration=7)
        elif level == Qgis.Success:
            self.iface.messageBar().pushMessage("KMZ Exporter", message, level=level, duration=5)

    def _display_configuration_dialog(self):
        """Obtains selected layers from canvas and launches configuration window."""
        selected_layers = self.iface.layerTreeView().selectedLayers()
        
        # Filter only vector layers
        vector_layers = [l for l in selected_layers if isinstance(l, QgsVectorLayer)]

        if not vector_layers:
            self.log_message("No vector layers selected in QGIS. Select layers and retry.", Qgis.Critical)
            self.CONTINUE = False
            return

        dialog = KMZExporterDialog(vector_layers)
        if dialog.exec_() == QDialog.Accepted:
            self.config = dialog.get_configuration()
        else:
            self.log_message("Process aborted by the user.", Qgis.Warning)
            self.CONTINUE = False

    def _input_check_inputs_validity(self):
        """
        Validates all user inputs, geometry integrity, and node assignments.
        Accumulates all detected errors to present them together.
        """
        self.log_message("Validating geometries and attributes...", Qgis.Info)

        errors = []  # Lista para acumular los mensajes de error

        # 1. Check Output Folder Path
        output_dir = self.config.get("output_dir", "")
        if not output_dir or not os.path.exists(output_dir):
            errors.append("Invalid or unselected output folder path.")

        # 2. Check Single Node Name
        is_single = self.config.get("is_single_node", True)
        if is_single:
            node_name = self.config.get("single_node_name", "")
            if not node_name:
                errors.append("Single Node mode selected, but no Node Name was provided.")

        # 3. Check Features Geometries and Node Fields across all layers
        node_field = self.config.get("node_field_name", "")

        for layer_cfg in self.config.get("layers", []):
            layer = layer_cfg["layer"]
            layer_name = layer.name()
            type_key = layer_cfg["type_key"]
            catalog_info = LAYER_CATALOG[type_key]

            # Verify node field exists if multi-node mode
            if not is_single:
                if layer.fields().indexOf(node_field) == -1:
                    errors.append(f"Node field '{node_field}' not found in layer '{layer_name}'.")

            for feature in layer.getFeatures():
                feat_id = feature.id()

                # Check Geometry Validity
                geom = feature.geometry()
                if geom.isNull() or geom.isEmpty():
                    errors.append(f"Layer '{layer_name}' -> Feature FID {feat_id}: Geometry is NULL or EMPTY.")

                # Check Node Field Null/Empty values in Multi-Node Mode
                if not is_single:
                    node_val = feature[node_field]
                    is_node_null = node_val is None or str(node_val).strip() in ("", "NULL", "null")
                    if is_node_null:
                        errors.append(f"Layer '{layer_name}' -> Feature FID {feat_id}: Node field '{node_field}' is NULL/Empty.")

                # Check Content Field Null/Empty values if layer requires content
                if catalog_info["has_content"]:
                    content_field = layer_cfg["content_field"]
                    content_val = feature[content_field]
                    is_content_null = content_val is None or str(content_val).strip() in ("", "NULL", "null")
                    if is_content_null:
                        errors.append(f"Layer '{layer_name}' -> Feature FID {feat_id}: Content field '{content_field}' is NULL/Empty.")

        # Manejo de resultados al finalizar el barrido completo
        if errors:
            self.CONTINUE = False
            
            # Imprime todos los errores en consola para registro técnico
            for err in errors:
                self.log_message(err, Qgis.Warning)

            # Muestra cuadro emergente amigable con el resumen completo
            error_summary = "\n".join(f"• {e}" for e in errors[:15])  # Muestra hasta 15 errores
            if len(errors) > 15:
                error_summary += f"\n\n... and {len(errors) - 15} more errors. Check QGIS console."

            QMessageBox.critical(
                None,
                "Validation Errors Found",
                f"Found {len(errors)} error(s) in the dataset:\n\n{error_summary}"
            )
        else:
            self.log_message("Validation completed successfully! All layers and features are valid.", Qgis.Success)

    def _process_and_group_features(self):
        """
        Reprojects coordinates to WGS84 (EPSG:4326), extracts feature names based on catalog
        rules, and groups all data per Node in a structured dictionary.
        """
        self.log_message("Processing geometries and reprojecting to EPSG:4326 (WGS84)...", Qgis.Info)

        target_crs = QgsCoordinateReferenceSystem("EPSG:4326")
        is_single = self.config.get("is_single_node", True)
        global_node_name = self.config.get("single_node_name", "NODO")
        node_field = self.config.get("node_field_name", "")

        for layer_cfg in self.config.get("layers", []):
            layer = layer_cfg["layer"]
            type_key = layer_cfg["type_key"]
            content_field = layer_cfg["content_field"]
            catalog_info = LAYER_CATALOG[type_key]

            # Set up coordinate transformation engine
            source_crs = layer.crs()
            transform = QgsCoordinateTransform(source_crs, target_crs, QgsProject.instance())

            for feature in layer.getFeatures():
                # Determine destination Node
                if is_single:
                    current_node = global_node_name
                else:
                    current_node = str(feature[node_field]).strip()

                if current_node not in self.processed_nodes:
                    self.processed_nodes[current_node] = {}

                if type_key not in self.processed_nodes[current_node]:
                    self.processed_nodes[current_node][type_key] = []

                # Determine Feature Name attribute
                if catalog_info["has_content"]:
                    feat_name = str(feature[content_field]) if feature[content_field] is not None else ""
                else:
                    feat_name = catalog_info.get("default_name", type_key)

                # Reproject geometry to WGS84
                geom = QgsGeometry(feature.geometry())
                geom.transform(transform)

                # Format coordinates string for KML
                coords_str = ""
                if catalog_info["geom"] == "Point":
                    point = geom.asPoint()
                    coords_str = f"{point.x()},{point.y()},0"
                
                elif catalog_info["geom"] == "LineString":
                    if geom.isMultipart():
                        lines = geom.asMultiPolyline()
                    else:
                        lines = [geom.asPolyline()]

                    coord_list = []
                    for line in lines:
                        for pt in line:
                            coord_list.append(f"{pt.x()},{pt.y()},0")
                    coords_str = " ".join(coord_list)

                self.processed_nodes[current_node][type_key].append({
                    "name": feat_name,
                    "coords": coords_str
                })

        self.log_message(f"Features successfully grouped into {len(self.processed_nodes)} node(s).", Qgis.Info)

    def _create_and_save_kmz(self):
        """
        Builds XML document structure, applies KML styling rules, sorts layers hierarchically,
        and compresses files into .kmz containers per Node.
        """
        self.log_message("Generating KML structure and compiling KMZ files...", Qgis.Info)
        output_dir = self.config.get("output_dir", "")

        for node_name, types_dict in self.processed_nodes.items():
            # Create XML Root
            kml = ET.Element("kml", xmlns="http://www.opengis.net/kml/2.2")
            doc = ET.SubElement(kml, "Document")
            doc_name = ET.SubElement(doc, "name")
            doc_name.text = node_name

            # Add Styles for used types in this node
            for type_key in types_dict.keys():
                catalog_info = LAYER_CATALOG[type_key]
                style = ET.SubElement(doc, "Style", id=f"style_{type_key.replace(' ', '_')}")

                if catalog_info["geom"] == "Point":
                    icon_style = ET.SubElement(style, "IconStyle")
                    
                    color_elem = ET.SubElement(icon_style, "color")
                    color_elem.text = catalog_info["color"]
                    
                    scale_elem = ET.SubElement(icon_style, "scale")
                    scale_elem.text = str(catalog_info["size"])
                    
                    icon_elem = ET.SubElement(icon_style, "Icon")
                    href_elem = ET.SubElement(icon_elem, "href")
                    href_elem.text = catalog_info["icon"]

                elif catalog_info["geom"] == "LineString":
                    line_style = ET.SubElement(style, "LineStyle")
                    
                    color_elem = ET.SubElement(line_style, "color")
                    color_elem.text = catalog_info["color"]
                    
                    width_elem = ET.SubElement(line_style, "width")
                    width_elem.text = str(catalog_info["width"])

            # Create Root Folder inside Document for Node
            node_folder = ET.SubElement(doc, "Folder")
            folder_name = ET.SubElement(node_folder, "name")
            folder_name.text = node_name

            # Sort types according to hierarchical order in catalog
            sorted_type_keys = sorted(types_dict.keys(), key=lambda k: LAYER_CATALOG[k]["order"])

            for type_key in sorted_type_keys:
                features_list = types_dict[type_key]
                catalog_info = LAYER_CATALOG[type_key]

                # Create subfolder for each FTTH entity category
                type_folder = ET.SubElement(node_folder, "Folder")
                type_folder_name = ET.SubElement(type_folder, "name")
                type_folder_name.text = type_key

                style_url_id = f"#style_{type_key.replace(' ', '_')}"

                for item in features_list:
                    placemark = ET.SubElement(type_folder, "Placemark")
                    
                    pm_name = ET.SubElement(placemark, "name")
                    pm_name.text = item["name"]

                    pm_style = ET.SubElement(placemark, "styleUrl")
                    pm_style.text = style_url_id

                    if catalog_info["geom"] == "Point":
                        point_geom = ET.SubElement(placemark, "Point")
                        coords_elem = ET.SubElement(point_geom, "coordinates")
                        coords_elem.text = item["coords"]

                    elif catalog_info["geom"] == "LineString":
                        line_geom = ET.SubElement(placemark, "LineString")
                        tess_elem = ET.SubElement(line_geom, "tessellate")
                        tess_elem.text = "1"
                        coords_elem = ET.SubElement(line_geom, "coordinates")
                        coords_elem.text = item["coords"]

            # Save temporary doc.kml and zip into .kmz
            temp_kml_path = os.path.join(output_dir, "doc.kml")
            final_kmz_path = os.path.join(output_dir, f"{node_name}.kmz")

            tree = ET.ElementTree(kml)
            tree.write(temp_kml_path, encoding="utf-8", xml_declaration=True)

            with zipfile.ZipFile(final_kmz_path, "w", zipfile.ZIP_DEFLATED) as kmz:
                kmz.write(temp_kml_path, arcname="doc.kml")

            # Clean up temporary KML file
            if os.path.exists(temp_kml_path):
                os.remove(temp_kml_path)

            self.log_message(f"Saved: {final_kmz_path}", Qgis.Info)

        self.log_message(f"SUCCESS! All {len(self.processed_nodes)} KMZ file(s) created in: {output_dir}", Qgis.Success)

    def run(self):
        """Main execution chain."""
        functions = [
            self._display_configuration_dialog,
            self._input_check_inputs_validity,
            self._process_and_group_features,
            self._create_and_save_kmz,
        ]

        for f in functions:
            if not self.CONTINUE:
                print(f"[CreateKMZ] Execution stopped before running {f.__name__}")
                break
            print(f"Running {f.__name__} " + 30 * "_")
            f()


# Execution trigger directly from QGIS Python Console
exporter = CreateKMZ(iface)
exporter.run()