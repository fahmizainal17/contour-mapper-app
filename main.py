# Import required libraries
import streamlit as st
from streamlit_folium import st_folium
import folium
import folium.plugins
import requests
import numpy as np
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter
from supabase import create_client, Client
import ezdxf
import io
import json
import os
import tempfile
from pyproj import Transformer
import streamlit.components.v1 as components

# Import custom styling function
from component import page_style

# Configure Streamlit page settings
st.set_page_config(
    page_title="Contour Map Generator",
    page_icon="🗺️",
    layout="wide"
)

# Apply custom styling
page_style()

# Load environment variables from Streamlit secrets
try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except KeyError as e:
    st.error(f"Missing required environment variable: {e}. Please set it in Streamlit secrets.")
    st.stop()

# Initialize Supabase client
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error(f"Failed to initialize Supabase client: {e}")
    st.stop()

# Configure coordinate projection (WGS84 to UTM Zone 48N)
transformer = Transformer.from_crs("EPSG:4326", "EPSG:32648", always_xy=True)

# Utility Functions
def project_coordinates(longitude: float, latitude: float) -> tuple:
    """
    Project geographic coordinates (longitude, latitude) to UTM Zone 48N.

    Args:
        longitude (float): The longitude coordinate.
        latitude (float): The latitude coordinate.

    Returns:
        tuple: A tuple of (x, y) coordinates in UTM Zone 48N.
    """
    x, y = transformer.transform(longitude, latitude)
    return x, y

def generate_grid(polygon_coordinates: list, spacing: float = 0.0005) -> list:
    """
    Generate a grid of points within the bounding box of a polygon.

    Args:
        polygon_coordinates (list): A list of (longitude, latitude) coordinates defining the polygon.
        spacing (float): The spacing between grid points in degrees. Defaults to 0.0005.

    Returns:
        list: A list of (latitude, longitude) grid points.

    Raises:
        Exception: If grid generation fails.
    """
    lats = [coord[1] for coord in polygon_coordinates]
    lons = [coord[0] for coord in polygon_coordinates]
    lat_min, lat_max = min(lats), max(lats)
    lon_min, lon_max = min(lons), max(lons)

    grid_points = []
    for lat in np.arange(lat_min, lat_max, spacing):
        for lon in np.arange(lon_min, lon_max, spacing):
            grid_points.append((lat, lon))
    
    return grid_points

def fetch_elevation(locations: list, chunk_size: int = 100) -> list:
    """
    Fetch elevation data for a list of locations using the Google Elevation API.

    Args:
        locations (list): A list of (latitude, longitude) coordinates.
        chunk_size (int): Number of locations to process per API request. Defaults to 100.

    Returns:
        list: A list of elevation values in meters.

    Raises:
        Exception: If the API request fails.
    """
    elevations = []
    for i in range(0, len(locations), chunk_size):
        chunk = locations[i:i + chunk_size]
        locations_str = "|".join([f"{lat},{lon}" for lat, lon in chunk])
        url = f"https://maps.googleapis.com/maps/api/elevation/json?locations={locations_str}&key={GOOGLE_API_KEY}"
        response = requests.get(url)
        data = response.json()
        
        if "results" in data:
            chunk_elevations = [res['elevation'] for res in data['results']]
            elevations.extend(chunk_elevations)
        else:
            elevations.extend([None] * len(chunk))
            st.warning(f"Error fetching elevation data for chunk {i // chunk_size + 1}. Using default values.")
    
    return elevations

def create_contour_dxf(grid: list, elevations: list, num_levels: int = 10) -> io.BytesIO:
    """
    Generate a DXF file with contour lines based on elevation data.

    Args:
        grid (list): A list of (latitude, longitude) grid points.
        elevations (list): A list of elevation values corresponding to the grid points.
        num_levels (int): Number of contour levels to generate. Defaults to 10.

    Returns:
        io.BytesIO: A stream containing the DXF file content.

    Raises:
        Exception: If contour generation or DXF creation fails.
    """
    # Convert to 2D elevation matrix
    lats = np.array([pt[0] for pt in grid])
    lons = np.array([pt[1] for pt in grid])
    unique_lats = np.unique(lats)
    unique_lons = np.unique(lons)
    
    # Create 2D grid for contour generation (projected coordinates)
    X, Y = np.meshgrid(unique_lons, unique_lats)
    
    # Reshape elevations into 2D grid
    z = np.zeros((len(unique_lats), len(unique_lons)))
    for i, lat in enumerate(unique_lats):
        for j, lon in enumerate(unique_lons):
            idx = np.where((lats == lat) & (lons == lon))[0]
            if len(idx) > 0:
                z[i, j] = elevations[idx[0]]
    
    # Handle NaN or infinite values
    if np.isnan(z).any() or np.isinf(z).any():
        z = np.nan_to_num(z, nan=np.nanmean(z))
    
    # Apply Gaussian filter
    z = gaussian_filter(z, sigma=1)
    
    # Create Elevation Grid visualization
    elevation_plot = plt.figure()
    plt.imshow(z, cmap='terrain')
    plt.colorbar(label='Elevation (m)')
    plt.title("Elevation Grid")
    st.session_state.elevation_grid_plot = elevation_plot
    
    # Create contours
    fig, ax = plt.subplots()
    min_elev = np.min(z)
    max_elev = np.max(z)
    levels = np.linspace(min_elev, max_elev, num_levels + 1)
    cs = ax.contour(X, Y, z, levels=levels)
    
    # Create Contour Visualization
    contour_plot = plt.figure()
    plt.contour(X, Y, z, levels=levels, cmap='viridis')
    plt.colorbar(label='Elevation (m)')
    plt.title("Contour Visualization")
    st.session_state.contour_plot = contour_plot
    
    # Create DXF document
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()
    entity_count = 0
    
    # Process each contour level
    for i, level in enumerate(cs.levels):
        segments = cs.allsegs[i]
        for segment in segments:
            if len(segment) < 2:
                continue
            points = [project_coordinates(x, y) + (0,) for x, y in segment]  # Z=0, elevation in 38 field
            polyline = msp.add_lwpolyline(points)
            polyline.dxf.layer = "0"  # Match QGIS layer
            polyline.dxf.elevation = level  # Set elevation in 38 field
            entity_count += 1
    
    # Save DXF to a temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.dxf') as tmp_file:
        doc.saveas(tmp_file.name)
        stream = io.BytesIO()
        with open(tmp_file.name, 'rb') as f:
            stream.write(f.read())
        stream.seek(0)
    
    # Clean up temporary file
    os.unlink(tmp_file.name)
    
    if len(stream.getvalue()) == 0:
        st.warning("DXF stream is empty, attempting fallback method.")
        return create_contour_dxf_fallback(grid, elevations, num_levels)
    
    return stream

def create_contour_dxf_fallback(grid: list, elevations: list, num_levels: int = 10) -> io.BytesIO:
    """
    Fallback method to generate a DXF file with contour lines if the primary method fails.

    Args:
        grid (list): A list of (latitude, longitude) grid points.
        elevations (list): A list of elevation values corresponding to the grid points.
        num_levels (int): Number of contour levels to generate. Defaults to 10.

    Returns:
        io.BytesIO: A stream containing the DXF file content.

    Raises:
        Exception: If contour generation or DXF creation fails.
    """
    # Convert to 2D elevation matrix
    lats = sorted(set([pt[0] for pt in grid]))
    lons = sorted(set([pt[1] for pt in grid]))
    
    elev_matrix = np.zeros((len(lats), len(lons)))
    for idx, (lat, lon) in enumerate(grid):
        i = lats.index(lat)
        j = lons.index(lon)
        elev_matrix[i, j] = elevations[idx]
    
    # Apply smoothing
    elev_matrix = gaussian_filter(elev_matrix, sigma=1)
    
    # Create contours
    fig, ax = plt.subplots()
    min_elev = np.min(elev_matrix)
    max_elev = np.max(elev_matrix)
    levels = np.linspace(min_elev, max_elev, num_levels + 1)
    X, Y = np.meshgrid(lons, lats)
    contour_plot = ax.contour(X, Y, elev_matrix, levels=levels)
    
    # Create DXF
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()
    entity_count = 0
    
    # Process each contour level
    for i, level in enumerate(contour_plot.levels):
        segments = contour_plot.allsegs[i]
        for segment in segments:
            if len(segment) < 2:
                continue
            points = [project_coordinates(x, y) + (0,) for x, y in segment]
            polyline = msp.add_lwpolyline(points)
            polyline.dxf.layer = "0"
            polyline.dxf.elevation = level
            entity_count += 1
    
    # Save DXF to a temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.dxf') as tmp_file:
        doc.saveas(tmp_file.name)
        stream = io.BytesIO()
        with open(tmp_file.name, 'rb') as f:
            stream.write(f.read())
        stream.seek(0)
    
    # Clean up temporary file
    os.unlink(tmp_file.name)
    
    if len(stream.getvalue()) == 0:
        st.error("Fallback DXF stream is empty. No content generated.")
        return stream
    
    return stream

# Main Application Logic
# Initialize polygon coordinates
polygon_coordinates = None

# Initialize session state for map and drawn GeoJSON
if 'drawn_geojson' not in st.session_state:
    st.session_state.drawn_geojson = None
if 'map_center' not in st.session_state:
    st.session_state.map_center = [3.1, 101.65]  # Default map center
if 'map_zoom' not in st.session_state:
    st.session_state.map_zoom = 14  # Default zoom level

# Attempt to load GeoJSON if uploaded
uploaded_geojson = st.file_uploader("Upload GeoJSON (optional)", type=["geojson", "json"])
if uploaded_geojson:
    try:
        geojson_data = json.load(uploaded_geojson)
        if "features" in geojson_data and geojson_data["features"]:
            if "geometry" in geojson_data["features"][0] and geojson_data["features"][0]["geometry"]["type"] == "Polygon":
                polygon_coordinates = geojson_data["features"][0]["geometry"]["coordinates"][0]
                st.session_state.drawn_geojson = geojson_data["features"][0]  # Save GeoJSON to session state
                st.success("Polygon loaded from GeoJSON.")
            else:
                st.error("The uploaded GeoJSON does not contain a valid polygon.")
        else:
            st.error("Invalid GeoJSON format: No features found.")
    except Exception as e:
        st.error(f"Error loading GeoJSON file: {e}")

# Always render the map, using session state for center and zoom
map_object = folium.Map(
    location=st.session_state.map_center,
    zoom_start=st.session_state.map_zoom
)
draw = folium.plugins.Draw(
    export=True,
    draw_options={
        'polyline': False,
        'polygon': True,
        'circle': False,
        'rectangle': True,
        'marker': False,
        'circlemarker': False
    },
    edit_options={'remove': True}
)
draw.add_to(map_object)

# Add previously drawn GeoJSON to the map if it exists
if st.session_state.drawn_geojson:
    folium.GeoJson(
        st.session_state.drawn_geojson,
        style_function=lambda _: {'fillColor': 'blue', 'color': 'blue', 'weight': 2, 'fillOpacity': 0.2}
    ).add_to(map_object)

# Render the map with increased size
output = st_folium(
    map_object,
    height=600,
    width="100%",
    returned_objects=["last_active_drawing", "center", "zoom"]
)

# Custom JavaScript/CSS to ensure Export button is below Delete button
components.html(
    """
    <style>
        /* Ensure Export button is below Delete button */
        .leaflet-draw-actions li:last-child a[title="Export"] {
            order: 2; /* Export button comes after Delete */
        }
        .leaflet-draw-actions li a[title="Delete"] {
            order: 1; /* Delete button comes before Export */
        }
    </style>
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            setTimeout(function() {
                const map = document.querySelector('div[data-testid="stFoliumMap"] iframe').contentWindow;
                map.on('draw:created', function(e) {
                    const geojson = e.layer.toGeoJSON();
                    localStorage.setItem('drawn_geojson', JSON.stringify(geojson));
                });
            }, 1000);
        });
    </script>
    """,
    height=0
)

# Update session state with map center and zoom
if output and "center" in output and "zoom" in output:
    st.session_state.map_center = [output["center"]["lat"], output["center"]["lng"]]
    st.session_state.map_zoom = output["zoom"]

# Save drawn GeoJSON to session state
if output and output["last_active_drawing"]:
    shape = output["last_active_drawing"]
    if shape['geometry']['type'] == 'Polygon':
        polygon_coordinates = shape['geometry']['coordinates'][0]  # [lng, lat]
        st.session_state.drawn_geojson = shape
        st.success("Polygon area selected from map.")
    else:
        st.warning("Please draw a polygon on the map.")

# Proceed with contour generation if polygon coordinates are defined
if polygon_coordinates is not None:
    # Initialize session state for plots, DXF stream, and upload status
    if 'elevation_grid_plot' not in st.session_state:
        st.session_state.elevation_grid_plot = None
    if 'contour_plot' not in st.session_state:
        st.session_state.contour_plot = None
    if 'dxf_stream' not in st.session_state:
        st.session_state.dxf_stream = None
    if 'upload_status' not in st.session_state:
        st.session_state.upload_status = None
    if 'upload_message' not in st.session_state:
        st.session_state.upload_message = None
    if 'file_name' not in st.session_state:
        st.session_state.file_name = None
    if 'message_displayed' not in st.session_state:
        st.session_state.message_displayed = False

    # Display plots if they exist in session state
    if st.session_state.elevation_grid_plot:
        st.pyplot(st.session_state.elevation_grid_plot)
    if st.session_state.contour_plot:
        st.pyplot(st.session_state.contour_plot)

    # Add resolution control
    col1, col2 = st.columns(2)
    with col1:
        grid_spacing = st.slider(
            "Grid Resolution",
            min_value=0.0002,
            max_value=0.001,
            value=0.0005,
            step=0.0001,
            format="%.4f",
            help="Lower values result in higher resolution but slower processing."
        )
    
    with col2:
        contour_levels = st.slider(
            "Contour Levels",
            min_value=5,
            max_value=20,
            value=10,
            step=1,
            help="Number of elevation contour lines to generate."
        )
    
    # Library version warning
    import ezdxf as ezdxf_check
    import matplotlib as mpl_check
    if not ezdxf_check.__version__.startswith('1.0'):
        st.warning("ezdxf version may be incompatible. Recommended: 1.0.3")

    if st.button("Generate Contours"):
        try:
            with st.spinner("Generating contours..."):
                grid_points = generate_grid(polygon_coordinates, spacing=grid_spacing)
                elevations = fetch_elevation(grid_points)
                dxf_stream = create_contour_dxf(grid_points, elevations, contour_levels)

            # Verify stream content
            dxf_stream.seek(0)
            stream_size = len(dxf_stream.getvalue())
            
            if stream_size == 0:
                st.error("Generated DXF file is empty.")
                st.session_state.dxf_stream = None
                st.session_state.elevation_grid_plot = None
                st.session_state.contour_plot = None
            else:
                st.success("DXF generated successfully.")
                dxf_stream.seek(0)
                st.session_state.dxf_stream = dxf_stream.read()
                st.session_state.upload_status = None
                st.session_state.upload_message = None
                st.session_state.file_name = None
                st.session_state.message_displayed = False
                if st.session_state.elevation_grid_plot:
                    st.pyplot(st.session_state.elevation_grid_plot)
                if st.session_state.contour_plot:
                    st.pyplot(st.session_state.contour_plot)
        except Exception as e:
            st.error(f"Error during contour generation: {e}")
            st.session_state.dxf_stream = None
            st.session_state.elevation_grid_plot = None
            st.session_state.contour_plot = None
            st.session_state.upload_status = None
            st.session_state.upload_message = None
            st.session_state.file_name = None
            st.session_state.message_displayed = False

    # Display download button if DXF stream exists in session state
    if st.session_state.dxf_stream:
        st.download_button(
            label="Download DXF",
            data=st.session_state.dxf_stream,
            file_name="contour.dxf",
            mime="application/octet-stream",
            key="download_dxf_button"
        )

        # Upload to Supabase
        if st.button("Upload to Supabase"):
            try:
                with st.spinner("Uploading to Supabase..."):
                    file_bytes = st.session_state.dxf_stream
                    if len(file_bytes) == 0:
                        raise ValueError("DXF stream is empty. Cannot upload an empty file.")
                    file_name = f"contour_{np.random.randint(1000)}.dxf"
                    response = supabase.storage.from_("dxf-files").upload(file_name, file_bytes)
                    if (hasattr(response, 'path') and response.path) or (hasattr(response, 'key') and response.key):
                        st.session_state.upload_status = True
                        st.session_state.upload_message = f"Successfully uploaded as `{file_name}` to Supabase."
                        st.session_state.file_name = file_name
                        st.session_state.message_displayed = False
                    else:
                        st.session_state.upload_status = False
                        st.session_state.upload_message = "Failed to upload to Supabase. No file path or key returned in the response."
                        st.session_state.message_displayed = False
            except Exception as e:
                st.session_state.upload_status = False
                error_message = f"Error uploading to Supabase: {str(e)}"
                if "Bucket not found" in str(e):
                    error_message += " (Bucket 'dxf-files' not found. Please verify the bucket exists in your Supabase project.)"
                st.session_state.upload_message = error_message
                st.session_state.message_displayed = False

    # Display upload status if it exists in session state and hasn't been displayed yet
    if st.session_state.upload_status is not None and not st.session_state.message_displayed:
        if st.session_state.upload_status:
            st.success(st.session_state.upload_message)
        else:
            st.error(st.session_state.upload_message)
        st.session_state.message_displayed = True

# Apply CSS for full-width map (adjusting for sidebar)
st.markdown(
    """
    <style>
        /* Ensure the main content area stretches to full width minus sidebar */
        div[data-testid="stAppViewContainer"] > div:first-child {
            width: 100%;
        }
        div[data-testid="stFoliumMap"] {
            width: 100% !important;
        }
        /* Style the sidebar */
        div[data-testid="stSidebar"] {
            background-color: #f0f2f6;
            padding: 10px;
        }
        /* Style the Leaflet Draw toolbar */
        .leaflet-draw {
            background: #fff;
            border-radius: 4px;
        }
        .leaflet-draw-toolbar a {
            background-color: #fff;
            color: #000;
        }
        .leaflet-draw-actions {
            display: flex;
            flex-direction: column;
        }
    </style>
    """,
    unsafe_allow_html=True
)