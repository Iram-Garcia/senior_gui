import streamlit as st
import os

st.title("Images Needing Verification")

script_dir = os.path.dirname(os.path.abspath(__file__))
verification_folder = os.path.join(script_dir, "..", "need_verification")
if os.path.exists(verification_folder):
    image_files = [f for f in os.listdir(verification_folder) if f.lower().endswith(('.jpg', '.png', '.jpeg'))]
    if image_files:
        for image_file in image_files:
            img_path = os.path.join(verification_folder, image_file)
            st.image(img_path, caption=image_file, use_container_width=True)
    else:
        st.write("No images found in the need_verification folder.")
else:
    st.write("The need_verification folder does not exist.")
