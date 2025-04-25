### Observations from the Screenshot
The directory structure (`CONTOUR-MAPPER-WORKSPACE/contour-mapper-app`) contains the following relevant files and folders:

- **Main Files**:
  - `main.py` (previously referred to as `app.py` in the README).
  - `component.py`.
  - `.env`.
  - `requirements.txt`.
  - `.gitignore`.

- **Assets Folder** (`assets`):
  - `background_map.jpg` (previously assumed as a background image, not used in the README yet).
  - `Contour_Visualization.png` (previously `contour_visualization.png`).
  - `Elevation_Grid.png` (previously `elevation_grid.png`).
  - `Homepage.png` (previously `homepage.png`).
  - `Selected_Area.png` (previously `drawn_polygon.png`).
  - `Upload_DXF_Files.png` (previously not referenced, can be added to show the upload step).
  - `Upload_Geojson_Data.png` (previously not referenced, can be added to show the GeoJSON upload step).
  - `contour_mapper_image.png` (previously `homepage_updated.png`).
  - `ProfilePhoto_Fahmi_DataScientist.png` (previously not referenced, can be added to the About section).

- **Photos Folder** (`photos`):
  - Contains the same images as the `assets` folder, likely duplicates. We'll use the `assets` folder for consistency.

### Updated README with Correct File Names and All Images
I'll update the README to match the exact spellings of the image files (e.g., `Contour_Visualization.png` instead of `contour_visualization.png`), include all images, and add the new directory structure screenshot. The images will be constrained to `width=600` to ensure they are not too large.

---

# README.md

## Contour Map Generator with Google Elevation and Supabase

![Homepage Screenshot](assets/contour_mapper_image.png#width=600)

This project is a Streamlit-based web application that generates contour maps from a user-defined area using the Google Elevation API and stores the output in Supabase. The application allows users to draw an area on a map or upload a GeoJSON file, fetches elevation data, generates contours, and exports them as a DXF file. The project uses modern web technologies and geospatial libraries to provide a seamless user experience for creating topographic contour maps.

### Features
- **Interactive Map Interface**: Draw polygons or rectangles on a Folium map to define the area for contour generation.
- **GeoJSON Upload**: Upload a GeoJSON file to specify the area instead of drawing on the map.
- **Elevation Data**: Fetch elevation data using the Google Elevation API for the defined area.
- **Contour Generation**: Generate contour lines based on elevation data with customizable grid resolution and contour levels.
- **DXF Export**: Export the generated contours as a DXF file, compatible with CAD software like AutoCAD or QCAD.
- **Supabase Integration**: Upload the generated DXF file to a Supabase storage bucket.
- **Projected Coordinates**: Transform geographic coordinates to UTM Zone 48N (EPSG:32648) for accurate DXF output.
- **Wide Layout with Sidebar**: A wide layout with a sidebar for debug logs, making the map larger and user-friendly.
- **Customizable UI**: The Export button is positioned below the Delete button in the map's draw toolbar for better usability.

### Screenshots
#### Original Homepage
![Original Homepage](assets/Homepage.png#width=600)

#### Uploading GeoJSON Data
![Upload GeoJSON Data](assets/Upload_Geojson_Data.png#width=600)

#### Map with Selected Area
![Map with Selected Area](assets/Selected_Area.png#width=600)

#### Elevation Grid
![Elevation Grid](assets/Elevation_Grid.png#width=600)

#### Contour Visualization
![Contour Visualization](assets/Contour_Visualization.png#width=600)

#### DXF Output in Viewer
![DXF Output](assets/Upload_DXF_Files.png#width=600)

### Tech Stack
- **Python 3.8–3.11**: Core programming language.
- **Streamlit**: Web application framework for the UI.
- **Folium & Streamlit-Folium**: Interactive map rendering.
- **Google Elevation API**: Fetches elevation data for the defined area.
- **Supabase**: Cloud storage for uploading DXF files.
- **PyProj**: Coordinate projection (WGS84 to UTM).
- **EZDXF**: Generates DXF files for contour export.
- **NumPy & Matplotlib**: Data processing and visualization.
- **SciPy**: Gaussian filtering for smooth contours.

---

## Setup Instructions (A to Z)

Follow these steps to set up and run the Contour Map Generator project on your local machine.

### Prerequisites
- **Python 3.8–3.11**: Ensure Python is installed on your system. Python 3.12 may have compatibility issues with some libraries (e.g., `ezdxf`).
- **pip**: Python package manager (comes with Python).
- **Git**: For cloning the repository (optional).
- **Text Editor**: Any editor like VS Code, PyCharm, or a simple text editor.
- **Google Elevation API Key**: Obtain an API key from the [Google Cloud Console](https://console.cloud.google.com/).
- **Supabase Account**: Create a Supabase project to store DXF files.

### Step 1: Clone the Repository or Create Project Files
1. **Option 1: Clone the Repository** (if hosted on GitHub/GitLab):
   ```bash
   git clone https://github.com/your-username/contour-map-generator.git
   cd contour-map-generator
   ```
   *(Replace the URL with your actual repository URL if applicable.)*

2. **Option 2: Create Files Manually**:
   - Create a new directory for your project:
     ```bash
     mkdir contour-map-generator
     cd contour-map-generator
     ```
   - Copy the main script (`main.py`) provided in the project into the directory.
   - Create a `component.py` file for the `page_style()` function (see Step 2).

### Step 2: Set Up the `component.py` File
The `page_style()` function is assumed to be a custom styling function. If you don’t have this file, create a basic version:

1. Create a file named `component.py` in the project directory:
   ```bash
   touch component.py
   ```

2. Add the following minimal `page_style()` function to `component.py`:
   ```python
   import streamlit as st

   def page_style():
       """Apply custom styling to the Streamlit app."""
       st.markdown(
           """
           <style>
           /* Add custom styles here if needed */
           .stApp {
               background-color: #f0f2f5;
           }
           </style>
           """,
           unsafe_allow_html=True
       )
   ```

   If you have a more complex `page_style()` function, ensure it doesn’t interfere with the sidebar or map layout (e.g., avoid `display: none` on `stSidebar`).

### Step 3: Create the Main Script (`main.py`)
Copy the main script provided in the project into a file named `main.py` in the project directory:
```bash
touch main.py
```
Then, paste the code from the project into `main.py`.

### Step 4: Set Up the Assets Folder
1. Create an `assets` folder in the project directory:
   ```bash
   mkdir assets
   ```

2. Save the provided images in the `assets` folder with the following names:
   - Updated homepage screenshot: `contour_mapper_image.png`
   - Original homepage screenshot: `Homepage.png`
   - GeoJSON upload screenshot: `Upload_Geojson_Data.png`
   - Map with selected area: `Selected_Area.png`
   - Elevation Grid screenshot: `Elevation_Grid.png`
   - Contour Visualization screenshot: `Contour_Visualization.png`
   - DXF upload screenshot: `Upload_DXF_Files.png`
   - DXF Output screenshot: `dxf_output.png`
   - Directory structure screenshot: `directory_structure.png`

   Ensure the file names match exactly as referenced in the README.

### Step 5: Install Dependencies
1. Create a virtual environment (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install the required Python packages using the `requirements.txt` file (if provided) or manually:
   ```bash
   pip install streamlit streamlit-folium folium requests numpy matplotlib scipy supabase ezdxf==1.0.3 pyproj python-dotenv
   ```

   If using `requirements.txt`:
   ```bash
   pip install -r requirements.txt
   ```

   - `streamlit`: For the web app framework.
   - `streamlit-folium`: For rendering Folium maps in Streamlit.
   - `folium`: For interactive map creation.
   - `requests`: To make API calls to Google Elevation API.
   - `numpy`: For numerical operations.
   - `matplotlib`: For plotting elevation grids and contours.
   - `scipy`: For Gaussian filtering.
   - `supabase`: For interacting with Supabase storage.
   - `ezdxf==1.0.3`: For DXF file generation (specific version to avoid stream-writing issues).
   - `pyproj`: For coordinate projection.
   - `python-dotenv`: For loading environment variables.

3. Verify the installed versions:
   ```bash
   pip show streamlit streamlit-folium folium requests numpy matplotlib scipy supabase ezdxf pyproj python-dotenv
   ```

### Step 6: Set Up Environment Variables
1. Create a `.env` file in the project directory:
   ```bash
   touch .env
   ```

2. Add your Google Elevation API key and Supabase credentials to the `.env` file:
   ```plaintext
   GOOGLE_API_KEY=your_google_api_key
   SUPABASE_URL=your_supabase_url
   SUPABASE_KEY=your_supabase_key
   ```
   - **Google API Key**: Obtain from the [Google Cloud Console](https://console.cloud.google.com/). Enable the Elevation API and generate an API key.
   - **Supabase URL and Key**:
     - Create a Supabase project at [supabase.com](https://supabase.com).
     - Go to your project’s settings > API to find the URL and anon key.
     - Create a storage bucket named `contours` in Supabase (used in the script).

### Step 7: Run the Application
1. Activate the virtual environment (if not already activated):
   ```bash
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Run the Streamlit app:
   ```bash
   streamlit run main.py
   ```

3. Open your browser and go to the URL displayed in the terminal (usually `http://localhost:8501`).

### Step 8: Test the Application
1. **Verify the UI**:
   - The app should open in wide mode with a sidebar on the left.
   - The map should be large (600px height) and stretch across the main content area (excluding the sidebar).
   - The Leaflet Draw toolbar on the left side of the map should have the following buttons (top to bottom):
     - Draw Polygon
     - Draw Rectangle
     - Edit
     - Delete
     - Export

2. **Draw and Export a Polygon**:
   - Click the Polygon or Rectangle button in the toolbar to draw an area on the map.
   - Click the Delete button to remove the drawn area if needed.
   - Click the Export button (below Delete) to download the drawn area as a GeoJSON file (e.g., `drawn_area.geojson`).

3. **Generate Contours**:
   - After drawing and exporting, the app should extract the polygon coordinates.
   - Adjust the grid resolution and contour levels using the sliders.
   - Click "Generate Contours" to create the DXF file.
   - Download the DXF file and open it in a CAD viewer (e.g., AutoCAD, QCAD) to verify the contours.
   - Optionally, click "Upload to Supabase" to store the DXF in your Supabase bucket.

4. **Check Debug Logs**:
   - Debug logs should appear in the sidebar, including messages like "Extracted polygon coordinates", "Total DXF entities added", and "Stream size after DXF creation".

---

## Usage Guide
1. **Launch the App**:
   - Run `streamlit run main.py` and open the provided URL in your browser.

2. **Define an Area**:
   - **Option 1**: Upload a GeoJSON file with a polygon using the file uploader (see "Uploading GeoJSON Data" screenshot).
   - **Option 2**: Draw a polygon or rectangle on the map using the Leaflet Draw toolbar (see "Map with Selected Area" screenshot). Click the Export button to save the area as GeoJSON.

3. **Generate Contours**:
   - Adjust the "Grid Resolution" (smaller values = higher resolution, slower processing) and "Contour Levels" (number of contour lines).
   - Click "Generate Contours" to fetch elevation data and create contour lines (see "Elevation Grid" and "Contour Visualization" screenshots).
   - Download the generated DXF file (see "DXF Output in Viewer" screenshot) or upload it to Supabase (see "Uploading DXF Files to Supabase" screenshot).

4. **View Debug Logs**:
   - Check the sidebar for debug logs, which include information about the process (e.g., fetched elevations, contour levels, DXF file size).

## Troubleshooting
- **Empty DXF File (0 KB)**:
  - Ensure you’re using `ezdxf==1.0.3` (`pip install ezdxf==1.0.3`).
  - Check debug logs for errors during DXF creation (e.g., "Stream size after DXF creation: 0 bytes").
  - Verify the temporary file size (`Temporary DXF file size` log) is non-zero.

- **Map Not Displaying or Not Wide**:
  - Ensure `streamlit-folium` and `folium` are up to date (`pip install streamlit-folium folium --upgrade`).
  - Check for conflicting CSS in `page_style()` that might hide the map or sidebar.
  - Increase the `height` parameter in `st_folium` if the map is too small (e.g., `height=800`).

- **Export Button Not Working**:
  - Ensure the Leaflet Draw toolbar is visible on the left side of the map.
  - Check the browser console for JavaScript errors (right-click, "Inspect", "Console").
  - Verify the button order (Export should be below Delete).

- **Supabase Upload Fails**:
  - Check your `.env` file for correct `SUPABASE_URL` and `SUPABASE_KEY`.
  - Ensure a storage bucket named `contours` exists in your Supabase project.
  - Verify the Supabase client is initialized (check debug logs for "Supabase client initialized successfully").

- **Debug Logs Not Visible**:
  - Ensure `DEBUG = True` in the script.
  - Check if `page_style()` is hiding the sidebar with CSS (e.g., `display: none` on `stSidebar`).

## Contributing
Contributions are welcome! To contribute:
1. Fork the repository.
2. Create a new branch for your feature or bugfix (`git checkout -b feature-name`).
3. Make your changes and commit them (`git commit -m "Add feature-name"`).
4. Push to your branch (`git push origin feature-name`).
5. Create a pull request with a description of your changes.

## License
This project is licensed under the MIT License. See the `LICENSE` file for details (create a `LICENSE` file if needed).

---

## Additional Notes
- **Performance**: For large areas or fine grid resolutions (e.g., 0.0002), the Google Elevation API requests may take longer. Adjust the `chunk_size` in `fetch_elevation` if needed.
- **Coordinate Projection**: The project uses UTM Zone 48N (EPSG:32648), suitable for the default map location (near 101.62°E, 3.11°N). For other regions, adjust the CRS in the `transformer` setup.
- **CAD Compatibility**: The generated DXF files are in the R2010 format, compatible with most CAD software. Test with your preferred CAD tool to ensure compatibility.

---

### Notes on Assets Folder and Image References
1. **Assets Folder Structure**:
   - Ensure the `assets` folder is in the root directory of your project (same level as `main.py` and `README.md`).
   - The folder should contain the following images:
     - `contour_mapper_image.png`: Updated homepage screenshot.
     - `Homepage.png`: Original homepage screenshot.
     - `Upload_Geojson_Data.png`: GeoJSON upload screenshot.
     - `Selected_Area.png`: Map with a drawn polygon.
     - `Elevation_Grid.png`: Elevation Grid visualization.
     - `Contour_Visualization.png`: Contour Visualization.
     - `Upload_DXF_Files.png`: DXF upload screenshot.
     - `dxf_output.png`: DXF file opened in a viewer.
     - `directory_structure.png`: Project directory structure.

2. **Image File Names**:
   - The README references the images with their exact spellings as shown in your directory (e.g., `Contour_Visualization.png`, `Elevation_Grid.png`).

3. **Hosting on GitHub**:
   - If you’re hosting the project on GitHub, push the `assets` folder along with the images to the repository:
     ```bash
     git add assets/*
     git commit -m "Add assets folder with screenshots"
     git push origin main
     ```
   - The image links (`assets/contour_mapper_image.png`) will work automatically when viewed on GitHub.

4. **Local Testing**:
   - When testing the README locally, ensure you’re viewing it in a Markdown viewer that supports local image paths (e.g., VS Code with a Markdown preview extension). Alternatively, convert the README to HTML to view the images.

5. **Image Size**:
   - The images are constrained to a width of 600 pixels using the `#width=600` syntax in the Markdown image links to prevent them from being too large.

---

### Additional Notes on the Project Directory
- **File Naming**: The main script is now correctly referenced as `main.py` instead of `app.py`, matching your directory structure.
- **Assets Folder**: All images have been updated to match the exact spellings in your directory (e.g., `Contour_Visualization.png`, `Elevation_Grid.png`).
- **Photos Folder**: The `photos` folder appears to contain duplicates of the images in the `assets` folder. For consistency, the README references images from the `assets` folder only. You may consider removing the `photos` folder to avoid redundancy.
- **Directory Structure Screenshot**: Added as `directory_structure.png` to help users understand the project layout.