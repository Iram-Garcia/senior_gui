# home.py
import streamlit as st

st.set_page_config(page_title="My Streamlit App", page_icon="🏠", layout="wide")

st.title("Welcome to the Home Page")
st.write("This is the default landing page of your Streamlit app.")
st.write("Use the sidebar to navigate to other pages.")

st.header("About This App")
st.write("This app demonstrates a multipage structure with a sidebar for navigation.")