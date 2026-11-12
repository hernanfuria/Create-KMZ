# Exportador KMZ Express - Redes FTTH para QGIS

Herramienta de automatización para **QGIS** diseñada para procesar, validar, transformar y exportar capas vectoriales de infraestructura de fibra óptica (**FTTH**) a archivos comprimidos **KMZ** (compatibles con Google Earth, Google Maps, Organic Maps y visualizadores GIS móviles).

El script está parametrizado mediante un catálogo configurable de elementos de red FTTH (`LAYER_CATALOG`).

---

## Índice

- [Características Principales](#características-principales)
- [Requisitos Previos](#requisitos-previos)
- [Cómo Ejecutar el Script en QGIS](#cómo-ejecutar-el-script-en-qgis)
- [Guía de Uso de la Interfaz Gráfica](#guía-de-uso-de-la-interfaz-gráfica)
  - [1. Estrategia de Agrupación por Nodo](#1-estrategia-de-agrupación-por-nodo)
  - [2. Configuración y Mapeo de Capas](#2-configuración-y-mapeo-de-capas)
  - [3. Carpeta de Salida y Exportación](#3-carpeta-de-salida-y-exportación)
- [Catálogo Técnico de Elementos](#catálogo-técnico-de-elementos)
- [Flujo de Procesamiento Interno](#flujo-de-procesamiento-interno)
- [Validaciones y Manejo de Errores](#validaciones-y-manejo-de-errores)
- [Estructura del KMZ Resultante](#estructura-del-kmz-resultante)

---

## Características Principales

- **Interfaz Gráfica Integrada (PyQt5):** Diálogo interactivo para mapear capas, seleccionar campos de atributos y configurar nodos.
- **Detección Inteligente por Coincidencia Difusa (*Fuzzy Matching*):** Asocia automáticamente los nombres de las capas cargadas con los tipos de elementos del catálogo, sin importar el orden de las palabras (ej. `200m_PRECONECTORIZADO` con `200m_PRECONECTORIZADO`).
- **Modos de Exportación:**
  - **Nodo Único (*Single Node*):** Exporta todas las capas seleccionadas a un solo archivo `.kmz`.
  - **Múltiples Nodos (*Multiple Nodes*):** Separa y genera archivos `.kmz` independientes automáticamente según un atributo de nodo (ej. campo `NODO`).
- **Reproyección Automática a WGS84 (`EPSG:4326`):** Transforma cualquier sistema de coordenadas de origen (ej. POSGAR, Gauss-Krüger, UTM) al estándar geográfico requerido por KML/KMZ.
- **Simbología y Estilos Preconfigurados:** Aplica colores (formato KML `aabbggrr`), grosores de línea e íconos oficiales de Google Earth para cada elemento de la red.
- **Auditoría y Validación Exhaustiva de Datos:** Inspecciona geometrías nulas/vacías y atributos faltantes antes de generar archivos, presentando un reporte unificado de inconsistencias.

---

## Requisitos Previos

1. **QGIS 3.x** instalado (versión 3.16 LTR o superior recomendada).
2. Proyecto de QGIS abierto con las capas vectoriales cargadas (Shapefiles, GeoPackage, etc.).
3. Acceso a la consola de Python integrada de QGIS. No se requieren librerías externas adicionales; el script utiliza módulos nativos de Python (`os`, `zipfile`, `xml.etree.ElementTree`, `difflib`, `re`) y las APIs de QGIS (`qgis.core`, `qgis.gui`, `qgis.PyQt`).

---

## Cómo Ejecutar el Script en QGIS

El script utiliza el objeto global `iface` provisto por el entorno interactivo de QGIS, por lo que **debe ejecutarse exclusivamente desde la Consola de Python de QGIS**.

### Paso a Paso:

1. **Abrir QGIS** y cargar el proyecto o las capas vectoriales que se desean exportar.
2. **Seleccionar las capas a exportar:**
   - En el panel **Capas** (*Layers Panel*) de QGIS, mantén presionada la tecla `Ctrl` o `Shift` y **selecciona todas las capas vectoriales** que formarán parte del KMZ (cajas, NAPs, preconectorizados, troncales, etc.).
   > ⚠️ **Importante:** Si no seleccionas ninguna capa vectorial antes de ejecutar el script, se mostrará un mensaje de advertencia y el proceso se cancelará.
3. **Abrir la Consola de Python:**
   - Ve al menú superior: **Complementos** (*Plugins*) -> **Consola de Python** (*Python Console*), o presiona el atajo de teclado `Ctrl + Alt + P`.
4. **Abrir el Editor de Código:**
   - En la barra de herramientas de la consola de Python, haz clic en el ícono del bloc de notas/lápiz (**Mostrar editor** / *Show Editor*).
5. **Cargar el script:**
   - En el editor, haz clic en el botón **Abrir script...** (*Open script*) y navega hasta el archivo `create_kmz_express_rosario.py`.
6. **Ejecutar el script:**
   - Haz clic en el botón verde **Ejecutar script** (*Run script*) o presiona `F5` con el editor activo.
7. Se abrirá la ventana emergente **FTTH KMZ Exporter Setup**.

---

## Guía de Uso de la Interfaz Gráfica

Al ejecutarse el script, se presenta el diálogo de configuración dividido en tres secciones principales:

```
┌────────────────────────────────────────────────────────────────────────┐
│                      FTTH KMZ Exporter Setup                           │
├────────────────────────────────────────────────────────────────────────┤
│ [1] Node Grouping Strategy                                            │
│   (o) Single Node (One global KMZ file)                                │
│       [ Ingrese nombre de nodo (ej: NODO_CENTRO) ]                     │
│   ( ) Multiple Nodes (Split into multiple KMZ files by field attribute)│
│       [ Desplegable con campos de atributo para nodo ]                 │
├────────────────────────────────────────────────────────────────────────┤
│ [2] Layer Configuration Table                                          │
│   Layer Name        | Entity Type Target     | Content Field (Name)    │
│   ------------------+------------------------+---------------------    │
│   CENTROS DE NODO   | CAJA EMPALME           | ID_EMPALME              │
│   NAP 80-20 x 8 b.  | NAP 80-20 x 8 bocas    | COD_NAP                 │
│   TRONCAL 144       | TRONCAL 144            | fid                     │
├────────────────────────────────────────────────────────────────────────┤
│ [3] Carpeta de salida y botones                                        │
│   [ C:/Ruta/Destino... ]  [ Browse Output Folder... ]                  │
│                                                                        │
│                                      [ Export KMZ ]  [ Cancel / Abort ]│
└────────────────────────────────────────────────────────────────────────┘
```

### 1. Estrategia de Agrupación por Nodo
- **Single Node (One global KMZ file):**
  - Activa la exportación unificada en un solo archivo `.kmz`.
  - Debes ingresar en la caja de texto el nombre del nodo o carpeta principal (por ejemplo, `NODO 07` o `NODO_SUR`).
- **Multiple Nodes (Split into multiple KMZ files by field attribute):**
  - Divide la red en múltiples archivos `.kmz` según el valor de un campo existente en las capas (por ejemplo, `NODO`, `SECTOR` o `ZONA`).
  - Habilita el menú desplegable para elegir cuál es el campo divisor.

### 2. Configuración y Mapeo de Capas
La tabla lista automáticamente todas las capas vectoriales seleccionadas en QGIS:
- **Layer Name:** Nombre de la capa en el árbol de capas (no editable).
- **Entity Type Target:** Menú desplegable con los tipos del catálogo FTTH. El script asigna una coincidencia preliminar automáticamente evaluando el nombre de la capa. Puedes cambiarla manualmente si deseas reasignar una categoría.
- **Content Field (Name Attribute):** Atributo de la capa que se utilizará como nombre visible de cada elemento en Google Earth. El script omite automáticamente atributos irrelevantes como `type` y `block_name` y selecciona el primer campo útil.

### 3. Carpeta de Salida y Exportación
- Haz clic en **Browse Output Folder...** para seleccionar la carpeta donde se guardarán los archivos `.kmz`.
- Presiona **Export KMZ** para iniciar la validación y generación.
- Presiona **Cancel / Abort** para cerrar sin realizar cambios.

---

## Catálogo Técnico de Elementos

El diccionario `LAYER_CATALOG` define la jerarquía, geometría, simbología y reglas de nombrado de cada elemento de red:

| Elemento | Geometría | Orden KML | Color (KML Hex) | Tamaño / Ancho | Estilo / Ícono |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **CO** | Punto | 1 | `ff000000` (Negro) | 2.4 | Cuadrado |
| **Splice Closure** | Punto | 2 | `ff631ee9` | 1.2 | Triángulo |
| **LCP** | Punto | 3 | `ffd4bc00` | 1.2 | Triángulo |
| **FAT** | Punto | 4 | `ff30b1f3` | 1.2 | Punto sombreado |
| **BACKBONE 144** | Línea | 5 | `ff0000ff` (Rojo) | Ancho: 3.0 | Línea troncal |
| **BACKBONE 24** | Línea | 9 | `ff00ff00` (Verde) | Ancho: 3.0 | Línea troncal |
| **BACKBONE 12** | Línea | 10 | `ffff00ff` (Magenta) | Ancho: 3.0 | Línea troncal |
| **LATERAL 12** | Línea | 11 | `ffff00ff` (Magenta) | Ancho: 1.2 | Línea lateral |

> **Nota sobre colores KML:** Los códigos de color KML se expresan en hexadecimal con formato `aabbggrr` (Alfa, Azul, Verde, Rojo), en lugar del orden estándar web `rrggbbaa`.

---

## Flujo de Procesamiento Interno

El método principal `run()` orquesta 4 fases secuenciales:

```
[Selección de Capas en QGIS]
             │
             ▼
 1. _display_configuration_dialog()
    - Interfaz gráfica PyQt
    - Coincidencia difusa de tipos
    - Captura de parámetros del usuario
             │
             ▼
 2. _input_check_inputs_validity()
    - Validación de directorio destino
    - Auditoría de geometrías nulas o vacías
    - Verificación de atributos requeridos
             │
             ▼
 3. _process_and_group_features()
    - Reproyección al CRS EPSG:4326 (WGS84)
    - Formateo de coordenadas para Point / LineString / MultiPolyline
    - Extracción de nombres y agrupación por Nodo y Tipo
             │
             ▼
 4. _create_and_save_kmz()
    - Construcción del árbol XML KML 2.2
    - Generación de estilos e inserción de Placemarks
    - Creación de doc.kml temporal y compresión ZIP a {nodo}.kmz
    - Limpieza de temporales y notificación de éxito
```

---

## Validaciones y Manejo de Errores

El script no exporta datos corruptos o incompletos. Durante la fase `_input_check_inputs_validity()`, realiza las siguientes comprobaciones:

1. **Directorio de salida:** Verifica que la ruta exista en el sistema de archivos.
2. **Nombre en Modo Nodo Único:** Confirma que el campo no esté vacío.
3. **Existencia del Campo de Nodo:** En modo multi-nodo, valida que el atributo seleccionado exista en todas las capas analizadas.
4. **Geometría Válida:** Verifica objeto por objeto (`feature.geometry()`) que no existan registros con geometrías nulas (`isNull()`) o vacías (`isEmpty()`).
5. **Atributos de Contenido Obligatorios:** Para elementos con `has_content: True` (como cajas, NAPs y límites), verifica que ningún registro tenga valores `NULL` o vacíos.

Si se detectan inconsistencias:
- El proceso se interrumpe antes de escribir ningún archivo.
- Los errores se imprimen en detalle en la consola de Python de QGIS.
- Se muestra un cuadro de diálogo de error (`QMessageBox.critical`) con una lista de las primeras inconsistencias encontradas y su identificador (`FID`), permitiendo localizarlas y corregirlas en QGIS rápidamente.

---

## Estructura del KMZ Resultante

Cada archivo `.kmz` generado sigue una estructura jerárquica estandarizada y limpia al abrirse en Google Earth:

```text
Nodo_Seleccionado.kmz
└── doc.kml
    └── Document [Nombre del Nodo]
        └── Carpeta Raíz [Nombre del Nodo]
            ├── CO/                    (Íconos cuadrados negros con IDs)
            ├── Splice Closure/        (Íconos triangulares morados con IDs)
            ├── LCP/                   (Íconos triangulares amarillos con IDs)
            ├── FAT/                   (Puntos celestes sombreados con IDs)
            ├── BACKBONE 144/          (Líneas rojas de 3.0 px)
            ├── BACKBONE 24/           (Líneas verdes de 3.0 px)
            ├── BACKBONE 12/           (Líneas magenta de 3.0 px)
            └── LATERAL 12/            (Líneas magenta de 1.2 px)
```

Al estar comprimido en formato KMZ, el archivo es ligero, autocontenido y listo para ser distribuido a técnicos de campo o clientes.
