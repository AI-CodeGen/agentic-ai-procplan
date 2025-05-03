import streamlit as st
import requests

API_URL = "http://localhost:8000"

st.title("Agentic AI ProcPlan UI")

st.header("1. Get Material Composition")
item = st.text_input("Enter item name:", "Laptop")
if st.button("Get Composition"):
    resp = requests.post(f"{API_URL}/v1/composition", json={"item": item})
    if resp.ok:
        data = resp.json()
        st.write("### Composition:")
        for comp in data["components"]:
            st.write(f"{comp['material']}: {comp['percentage']}%")
    else:
        st.error(f"Error: {resp.text}")

st.header("2. Get Market Prices for Materials")
materials = []
for i in range(5):
    mat = st.text_input(f"Material {i+1}", "" if i > 0 else "Steel")
    materials.append(mat)
if st.button("Get Market Prices"):
    if all(materials):
        resp = requests.post(f"{API_URL}/v1/marketprice", json={"materials": materials})
        if resp.ok:
            data = resp.json()
            st.write("### Market Prices:")
            for mat, price in data["prices"].items():
                st.write(f"{mat}: ${price}")
        else:
            st.error(f"Error: {resp.text}")
    else:
        st.warning("Please enter all 5 materials.")
