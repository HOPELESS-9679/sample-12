import streamlit as st
import pandas as pd
import folium
from folium.plugins import MarkerCluster
from geopy.distance import geodesic
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
import requests
import io
from github import Github  # PyGithub library

# Set page config
st.set_page_config(
    page_title="Nursery Locator - Khariar",
    page_icon="🌿",
    layout="wide"
)

# Initialize GitHub access
@st.cache_data
def init_github():
    # Create a personal access token: https://github.com/settings/tokens
    # Add it to Streamlit secrets (settings -> Secrets) as GITHUB_TOKEN
    if 'GITHUB_TOKEN' in st.secrets:
        return Github(st.secrets['GITHUB_TOKEN'])
    return None

# Load data from GitHub
@st.cache_data
def load_data(github):
    try:
        if github:
            repo = github.get_repo("your-username/nursery-locator")
            excel_file = repo.get_contents("NURSARY.xlsx")
            data = pd.read_excel(io.BytesIO(excel_file.decoded_content))
        else:
            # Fallback to direct URL (make sure it's raw content)
            excel_url = "https://github.com/your-username/nursery-locator/raw/main/NURSARY.xlsx"
            data = pd.read_excel(excel_url)
        
        # Validate required columns
        required_columns = ['Name', 'Longitude', 'Latitude', 'Capacity', 'PlantsAvailable', 'Contact']
        for col in required_columns:
            if col not in data.columns:
                data[col] = 'N/A'
        return data
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return None

@st.cache_data
def load_khariar_boundary(github):
    try:
        if github:
            repo = github.get_repo("your-username/nursery-locator")
            geojson_file = repo.get_contents("khariar_boundary.geojson")
            return geojson_file.decoded_content.decode('utf-8')
        else:
            # Fallback to direct URL
            geo_json_url = "https://github.com/your-username/nursery-locator/raw/main/khariar_boundary.geojson"
            response = requests.get(geo_json_url)
            return response.text
    except Exception as e:
        st.warning(f"Could not load Khariar boundary: {str(e)}")
        return '{"type": "FeatureCollection", "features": []}'

def create_map(data, boundary_data, user_location=None):
    m = folium.Map(location=[20.1, 82.5], zoom_start=11)
    
    # Add boundary
    try:
        boundary_json = json.loads(boundary_data)
        if boundary_json['features']:
            folium.GeoJson(
                boundary_json,
                name='Khariar Boundary',
                style_function=lambda x: {
                    'color': 'yellow',
                    'weight': 3,
                    'fillOpacity': 0.1
                }
            ).add_to(m)
    except:
        pass
    
    # Add nurseries
    marker_cluster = MarkerCluster().add_to(m)
    for _, row in data.iterrows():
        folium.Marker(
            [row['Latitude'], row['Longitude']],
            popup=f"""
            <b>{row['Name']}</b><br>
            Capacity: {row['Capacity']}<br>
            Plants: {row['PlantsAvailable']}<br>
            Contact: {row['Contact']}
            """,
            icon=folium.Icon(icon='leaf', prefix='fa', color='green')
        ).add_to(marker_cluster)
    
    # Add user location if provided
    if user_location:
        folium.Marker(
            user_location,
            icon=folium.Icon(color='blue', icon='user', prefix='fa'),
            tooltip="Your Location"
        ).add_to(m)
        
        # Find nearest nursery
        nearest = min(
            [(row['Latitude'], row['Longitude']) for _, row in data.iterrows()],
            key=lambda loc: geodesic(user_location, loc).km
        )
        folium.PolyLine(
            [user_location, nearest],
            color='red',
            weight=2
        ).add_to(m)
        m.fit_bounds([user_location, nearest])
    
    return m

def main():
    st.title("🌿 Khariar Nursery Locator")
    
    # Initialize GitHub
    github = init_github()
    
    # Load data
    data = load_data(github)
    boundary = load_khariar_boundary(github)
    
    if data is not None:
        st.sidebar.header("Options")
        
        # Location input
        address = st.sidebar.text_input("Enter your location in Khariar:")
        user_loc = None
        if address:
            try:
                geolocator = Nominatim(user_agent="khariar_app")
                location = geolocator.geocode(f"{address}, Khariar, India")
                if location:
                    user_loc = (location.latitude, location.longitude)
                    st.sidebar.success(f"Location found: {location.address}")
                else:
                    st.sidebar.warning("Location not found")
            except Exception as e:
                st.sidebar.error(f"Geocoding error: {str(e)}")
        
        # Create and show map
        m = create_map(data, boundary, user_loc)
        st_folium(m, width=1200, height=700)
        
        # Show data
        if st.sidebar.checkbox("Show raw data"):
            st.dataframe(data)

if __name__ == "__main__":
    import json
    main()