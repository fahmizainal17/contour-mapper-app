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
import base64
import json
import os
import tempfile
from dotenv import load_dotenv
import traceback
from pyproj import Transformer
import streamlit.components.v1 as components

# Assuming page_style() is a custom function for styling
from component import page_style

# --- SET PAGE CONFIG AS THE FIRST COMMAND ---
st.set_page_config(
    page_title="Contour Map Generator",
    page_icon="🗺️",
    layout="wide"
)

# Apply custom styling (after set_page_config)
page_style()

# --- ENABLE DEBUG MODE ---
DEBUG = True

def debug_print(msg):
    """Helper function to print debug messages (in sidebar)"""
    if DEBUG:
        with st.sidebar:
            st.info(f"DEBUG: {msg}")

# --- CONFIG ---
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# --- INIT SUPABASE ---
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    debug_print("Supabase client initialized successfully")
except Exception as e:
    st.error(f"Failed to initialize Supabase client: {e}")
    debug_print(f"Supabase initialization error: {traceback.format_exc()}")

# --- COORDINATE PROJECTION ---
# Transform from WGS84 (EPSG:4326) to UTM Zone 48N (EPSG:32648)
transformer = Transformer.from_crs("EPSG:4326", "EPSG:32648", always_xy=True)

def project_coordinates(lon, lat):
    """Project geographic coordinates (lon, lat) to UTM Zone 48N."""
    x, y = transformer.transform(lon, lat)
    return x, y

# --- STREAMLIT UI ---
st.title("🗺️ Contour Map Generator with Google Elevation + Supabase")

st.markdown("""
1. Draw or load area.
2. Get elevation.
3. Generate contours.
4. Download DXF or upload to Supabase.
""")

# --- LOAD GEOJSON (OPTIONAL) ---
uploaded_geojson = st.file_uploader("Upload GeoJSON (optional)", type=["geojson", "json"])
polygon_coords = None

if uploaded_geojson:
    try:
        geojson_data = json.load(uploaded_geojson)
        debug_print(f"Loaded GeoJSON: {json.dumps(geojson_data)[:200]}...")
        
        try:
            polygon_coords = geojson_data["features"][0]["geometry"]["coordinates"][0]
            debug_print(f"Extracted polygon coordinates (first 3): {polygon_coords[:3]}")
            debug_print(f"Total points in polygon: {len(polygon_coords)}")
            st.success("Polygon loaded from GeoJSON.")
        except Exception as e:
            st.error(f"Invalid GeoJSON format: {e}")
            debug_print(f"GeoJSON extraction error: {traceback.format_exc()}")
    except Exception as e:
        st.error(f"Error loading GeoJSON file: {e}")
        debug_print(f"GeoJSON loading error: {traceback.format_exc()}")

# --- MAP INTERFACE IF NO GEOJSON ---
if not polygon_coords:
    debug_print("No polygon coordinates from GeoJSON, showing map interface")
    
    # Initialize session state for storing drawn GeoJSON
    if 'drawn_geojson' not in st.session_state:
        st.session_state.drawn_geojson = None
    
    # Create the Folium map
    m = folium.Map(location=[3.1, 101.65], zoom_start=14)
    draw = folium.plugins.Draw(
        export=True,  # Enable the default export button on the map
        draw_options={
            'polyline': False,
            'polygon': True,
            'circle': False,
            'rectangle': True,  # Allow box (rectangle) drawing
            'marker': False,
            'circlemarker': False
        },
        edit_options={
            'remove': True  # Enable delete button
        }
    )
    draw.add_to(m)
    
    # Render the map with increased size
    out = st_folium(m, height=600, width="100%", returned_objects=["last_active_drawing"])
    
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
                        // Optionally store the GeoJSON for further use
                        localStorage.setItem('drawn_geojson', JSON.stringify(geojson));
                    });
                }, 1000);
            });
        </script>
        """,
        height=0
    )
    
    # Save drawn GeoJSON to session state
    if out and out["last_active_drawing"]:
        debug_print(f"Drawing received from map: {json.dumps(out['last_active_drawing'])[:200]}...")
        shape = out["last_active_drawing"]
        if shape['geometry']['type'] == 'Polygon':
            polygon_coords = shape['geometry']['coordinates'][0]  # [lng, lat]
            debug_print(f"Extracted polygon coordinates (first 3): {polygon_coords[:3]}")
            debug_print(f"Total points in polygon: {len(polygon_coords)}")
            st.success("Polygon area selected from map.")
            st.session_state.drawn_geojson = shape  # Save to session state
        else:
            debug_print(f"Drew a {shape['geometry']['type']}, not a Polygon")

# --- UTILITY FUNCTION: GENERATE GRID ---
def generate_grid(polygon, spacing=0.0005):
    try:
        lats = [coord[1] for coord in polygon]
        lons = [coord[0] for coord in polygon]
        lat_min, lat_max = min(lats), max(lats)
        lon_min, lon_max = min(lons), max(lons)
        
        debug_print(f"Lat range: {lat_min} to {lat_max}")
        debug_print(f"Lon range: {lon_min} to {lon_max}")

        grid_points = []
        for lat in np.arange(lat_min, lat_max, spacing):
            for lon in np.arange(lon_min, lon_max, spacing):
                grid_points.append((lat, lon))
        
        debug_print(f"Generated grid with {len(grid_points)} points")
        debug_print(f"First few grid points: {grid_points[:3]}")
        return grid_points
    except Exception as e:
        debug_print(f"Error generating grid: {traceback.format_exc()}")
        raise

# --- UTILITY FUNCTION: FETCH ELEVATION ---
def fetch_elevation(locations, chunk_size=100):
    try:
        elevations = []
        debug_print(f"Fetching elevation for {len(locations)} locations in chunks of {chunk_size}")
        
        for i in range(0, len(locations), chunk_size):
            chunk = locations[i:i + chunk_size]
            locations_str = "|".join([f"{lat},{lon}" for lat, lon in chunk])
            
            debug_print(f"Fetching chunk {i // chunk_size + 1}/{(len(locations) + chunk_size - 1) // chunk_size}")
            url = f"https://maps.googleapis.com/maps/api/elevation/json?locations={locations_str}&key={GOOGLE_API_KEY}"
            r = requests.get(url)
            data = r.json()
            
            if "results" in data:
                chunk_elevations = [res['elevation'] for res in data['results']]
                elevations.extend(chunk_elevations)
                debug_print(f"Got {len(chunk_elevations)} elevations. First few: {chunk_elevations[:3]}")
            else:
                debug_print(f"API Error: {data}")
                elevations.extend([None] * len(chunk))
                st.warning(f"Error fetching elevation data for chunk {i // chunk_size + 1}. Using default values.")
        
        debug_print(f"Total elevations fetched: {len(elevations)}")
        debug_print(f"Elevation range: {min([e for e in elevations if e is not None])} to {max([e for e in elevations if e is not None])}")
        return elevations
    except Exception as e:
        debug_print(f"Error fetching elevations: {traceback.format_exc()}")
        raise

# --- UTILITY FUNCTION: CREATE CONTOUR DXF ---
def create_contour_dxf(grid, elevations, num_levels=10):
    try:
        # Convert to 2D elevation matrix
        lats = np.array([pt[0] for pt in grid])
        lons = np.array([pt[1] for pt in grid])
        
        # Get unique values for reshaping
        unique_lats = np.unique(lats)
        unique_lons = np.unique(lons)
        debug_print(f"Unique lats: {len(unique_lats)}, Unique lons: {len(unique_lons)}")
        
        # Create 2D grid for contour generation (projected coordinates)
        X, Y = np.meshgrid(unique_lons, unique_lats)
        X_utm, Y_utm = transformer.transform(X, Y)
        
        # Reshape elevations into 2D grid
        z = np.zeros((len(unique_lats), len(unique_lons)))
        for i, lat in enumerate(unique_lats):
            for j, lon in enumerate(unique_lons):
                idx = np.where((lats == lat) & (lons == lon))[0]
                if len(idx) > 0:
                    z[i, j] = elevations[idx[0]]
        
        debug_print(f"Elevation matrix shape: {z.shape}")
        
        # Handle NaN or infinite values
        if np.isnan(z).any() or np.isinf(z).any():
            debug_print("Warning: NaN or Inf values detected in elevation data")
            z = np.nan_to_num(z, nan=np.nanmean(z))
            
        # Apply Gaussian filter
        z = gaussian_filter(z, sigma=1)
        debug_print("Applied Gaussian filter")
        
        # Create debug visualization
        debug_plot = plt.figure()
        plt.imshow(z, cmap='terrain')
        plt.colorbar(label='Elevation (m)')
        plt.title("Elevation Grid")
        st.pyplot(debug_plot)
        
        # Create contours
        debug_print("Creating contours...")
        fig, ax = plt.subplots()
        
        # Calculate contour levels
        min_elev = np.min(z)
        max_elev = np.max(z)
        levels = np.linspace(min_elev, max_elev, num_levels + 1)
        debug_print(f"Contour levels: {levels}")
        
        cs = ax.contour(X, Y, z, levels=levels)
        
        # Create contour visualization
        debug_plot2 = plt.figure()
        plt.contour(X, Y, z, levels=levels, cmap='viridis')
        plt.colorbar(label='Elevation (m)')
        plt.title("Contour Visualization")
        st.pyplot(debug_plot2)
        
        # Create DXF document
        debug_print("Creating DXF document...")
        doc = ezdxf.new('R2010')
        msp = doc.modelspace()
        entity_count = 0
        
        # Process each contour level
        for i, level in enumerate(cs.levels):
            debug_print(f"Processing contour level {i+1}/{len(cs.levels)} ({level:.2f}m)")
            
            # Get contour segments using allsegs
            segments = cs.allsegs[i]
            debug_print(f"Level {level:.2f}m has {len(segments)} segments")
            
            for segment in segments:
                if len(segment) < 2:
                    debug_print(f"Skipping invalid segment at level {level:.2f}m (length: {len(segment)})")
                    continue
                
                # Project coordinates to UTM
                points = [project_coordinates(x, y) + (0,) for x, y in segment]  # Z=0, elevation in 38 field
                debug_print(f"First few projected points for level {level:.2f}m: {points[:3]}")
                
                # Add polyline to DXF
                polyline = msp.add_lwpolyline(points)
                polyline.dxf.layer = "0"  # Match QGIS layer
                polyline.dxf.elevation = level  # Set elevation in 38 field
                entity_count += 1
        
        debug_print(f"Total DXF entities added: {entity_count}")
        
        # Verify DXF content
        entities = list(msp.query('*'))
        debug_print(f"DXF modelspace contains {len(entities)} entities")
        
        # Save DXF to a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.dxf') as tmp_file:
            doc.saveas(tmp_file.name)
            tmp_file_size = os.path.getsize(tmp_file.name)
            debug_print(f"Temporary DXF file size: {tmp_file_size} bytes")
            
            # Read temporary file into stream
            stream = io.BytesIO()
            with open(tmp_file.name, 'rb') as f:
                stream.write(f.read())
            stream.seek(0)
            stream_size = len(stream.getvalue())
            debug_print(f"Stream size after DXF creation: {stream_size} bytes")
            
        # Clean up temporary file
        os.unlink(tmp_file.name)
        
        if stream_size == 0:
            st.warning("DXF stream is empty, attempting fallback method")
            return create_contour_dxf_fallback(grid, elevations, num_levels)
        
        debug_print("DXF file created successfully")
        return stream
    except Exception as e:
        debug_print(f"Error creating contour DXF: {traceback.format_exc()}")
        st.error(f"Error creating contour DXF: {e}")
        return create_contour_dxf_fallback(grid, elevations, num_levels)

# --- UTILITY FUNCTION: CREATE CONTOUR DXF FALLBACK ---
def create_contour_dxf_fallback(grid, elevations, num_levels=10):
    try:
        debug_print("Using fallback method for DXF creation")
        
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
            debug_print(f"Level {level:.2f}m has {len(segments)} segments")
            
            for segment in segments:
                if len(segment) < 2:
                    debug_print(f"Skipping invalid segment at level {level:.2f}m (length: {len(segment)})")
                    continue
                
                # Project coordinates to UTM
                points = [project_coordinates(x, y) + (0,) for x, y in segment]
                debug_print(f"First few projected points for level {level:.2f}m (fallback): {points[:3]}")
                
                # Add polyline to DXF
                polyline = msp.add_lwpolyline(points)
                polyline.dxf.layer = "0"
                polyline.dxf.elevation = level
                entity_count += 1
        
        debug_print(f"Total DXF entities added (fallback): {entity_count}")
        
        # Verify DXF content
        entities = list(msp.query('*'))
        debug_print(f"DXF modelspace contains {len(entities)} entities (fallback)")
        
        # Save DXF to a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.dxf') as tmp_file:
            doc.saveas(tmp_file.name)
            tmp_file_size = os.path.getsize(tmp_file.name)
            debug_print(f"Temporary DXF file size (fallback): {tmp_file_size} bytes")
            
            # Read temporary file into stream
            stream = io.BytesIO()
            with open(tmp_file.name, 'rb') as f:
                stream.write(f.read())
            stream.seek(0)
            stream_size = len(stream.getvalue())
            debug_print(f"Stream size after DXF creation (fallback): {stream_size} bytes")
            
        # Clean up temporary file
        os.unlink(tmp_file.name)
        
        if stream_size == 0:
            st.error("Fallback DXF stream is empty, no content generated")
            return stream
        
        debug_print("Fallback DXF file created successfully")
        return stream
    except Exception as e:
        debug_print(f"Fallback method failed: {traceback.format_exc()}")
        st.error(f"Fallback DXF creation failed: {e}")
        
        # Return empty DXF
        doc = ezdxf.new('R2010')
        stream = io.BytesIO()
        doc.saveas(stream)
        stream.seek(0)
        return stream

# --- MAIN WORKFLOW ---
if polygon_coords:
    debug_print("Polygon coordinates detected, ready to generate contours")
    
    # Add resolution control
    col1, col2 = st.columns(2)
    with col1:
        grid_spacing = st.slider("Grid Resolution", 0.0002, 0.001, 0.0005, 0.0001, 
                                format="%.4f", 
                                help="Lower values = higher resolution but slower processing")
    
    with col2:
        contour_levels = st.slider("Contour Levels", 5, 20, 10, 1,
                                  help="Number of elevation contour lines to generate")
    
    # Library version warning
    import ezdxf as ezdxf_check
    import matplotlib as mpl_check
    debug_print(f"Using ezdxf version: {ezdxf_check.__version__}, matplotlib version: {mpl_check.__version__}")
    if not ezdxf_check.__version__.startswith('1.0'):
        st.warning("ezdxf version may be incompatible. Recommended: 1.0.3")
    
    if st.button("🔄 Generate Contours"):
        try:
            with st.spinner("Generating..."):
                debug_print("Starting contour generation workflow")
                grid_points = generate_grid(polygon_coords, spacing=grid_spacing)
                elevations = fetch_elevation(grid_points)
                dxf_stream = create_contour_dxf(grid_points, elevations, contour_levels)

            # Verify stream content
            dxf_stream.seek(0)
            stream_size = len(dxf_stream.getvalue())
            debug_print(f"Final stream size before download: {stream_size} bytes")
            
            if stream_size == 0:
                st.error("Generated DXF file is empty. Check debug logs for details.")
            else:
                st.success("DXF generated successfully.")

                # --- Download Button ---
                dxf_stream.seek(0)
                b64 = base64.b64encode(dxf_stream.read()).decode()
                href = f'<a href="data:application/octet-stream;base64,{b64}" download="contour.dxf">📥 Download DXF</a>'
                st.markdown(href, unsafe_allow_html=True)
                debug_print("DXF ready for download")
                
                # Reset file pointer for potential upload
                dxf_stream.seek(0)

                # --- Upload to Supabase ---
                if st.button("☁️ Upload to Supabase"):
                    try:
                        file_bytes = dxf_stream.read()
                        file_name = f"contour_{np.random.randint(1000)}.dxf"
                        debug_print(f"Uploading to Supabase as {file_name}")
                        res = supabase.storage.from_("contours").upload(file_name, file_bytes)
                        st.success(f"Uploaded as `{file_name}` to Supabase.")
                        debug_print("Supabase upload successful")
                    except Exception as e:
                        st.error(f"Error uploading to Supabase: {e}")
                        debug_print(f"Supabase upload error: {traceback.format_exc()}")
        except Exception as e:
            st.error(f"Error during contour generation: {e}")
            debug_print(f"Contour generation error: {traceback.format_exc()}")
else:
    debug_print("No polygon coordinates available")
    st.warning("Please draw a polygon on the map and click the Export button on the map to save the area.")

# --- CSS for Full Width Map (Adjusting for Sidebar) ---
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
    /* Optional: Style the sidebar */
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