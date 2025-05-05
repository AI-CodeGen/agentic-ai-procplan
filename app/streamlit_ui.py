import streamlit as st
import requests
from requests.exceptions import RequestException
from config import settings

API_URL = "http://localhost:8000"
TIMEOUT = settings.STREAMLIT_UI_TIMEOUT_SECONDS  # 5 seconds timeout

st.title("Agentic AI ProcPlan UI")

# Initialize session state for materials if not exists
if 'materials' not in st.session_state:
    st.session_state.materials = [""] * 5

st.header("1. Get Material Composition")
item = st.text_input("Enter item name:", "Laptop")
if st.button("Get Composition"):
    try:
        resp = requests.post(f"{API_URL}/v1/composition", json={"item": item}, timeout=TIMEOUT)
        if resp.ok:
            data = resp.json()
            st.write("### Composition:")
            # Update session state with materials from composition
            materials = []
            for i, comp in enumerate(data["components"]):
                st.write(f"{comp['material']}: {comp['percentage']}%")
                materials.append(comp['material'])
            # Pad with empty strings if less than 5 materials
            while len(materials) < 5:
                materials.append("")
            st.session_state.materials = materials
        else:
            st.error(f"Error: {resp.text}")
    except RequestException as e:
        st.error(f"Connection error: Could not connect to the API server. Please ensure the FastAPI server is running at {API_URL}")
        st.info("To start the server, run: uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")

st.header("2. Get Market Prices for Materials")
# Create text inputs with values from session state
for i in range(5):
    st.session_state.materials[i] = st.text_input(
        f"Material {i+1}", 
        st.session_state.materials[i] if st.session_state.materials[i] else ""
    )

if st.button("Get Market Prices"):
    # Filter out empty materials
    valid_materials = [mat for mat in st.session_state.materials if mat]
    if len(valid_materials) > 0:
        try:
            resp = requests.post(f"{API_URL}/v1/marketprice", json={"materials": valid_materials}, timeout=TIMEOUT)
            if resp.ok:
                data = resp.json()
                st.write("### Market Prices:")
                for mat, price in data["prices"].items():
                    st.write(f"{mat}: ${price}")
            else:
                st.error(f"Error: {resp.text}")
        except RequestException as e:
            st.error(f"Connection error: Could not connect to the API server. Please ensure the FastAPI server is running at {API_URL}")
            st.info("To start the server, run: uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
    else:
        st.warning("Please enter at least one material.")
