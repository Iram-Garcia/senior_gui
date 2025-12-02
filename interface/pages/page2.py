"""
Page 2: Manual Review of Low-Confidence Detections
Review and correct misread license plates from the verification folder.
"""
import streamlit as st
import os
from pathlib import Path
from PIL import Image
import pandas as pd
from student_db import verify_scanned_plate, get_all_students

# Get paths
SCRIPT_DIR = Path(__file__).resolve().parent
INTERFACE_DIR = SCRIPT_DIR.parent
VERIFICATION_FOLDER = INTERFACE_DIR / "need_verification"


def get_images_in_folder():
    """Get list of images in the verification folder."""
    if not VERIFICATION_FOLDER.exists():
        return []
    
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif'}
    images = [
        f for f in VERIFICATION_FOLDER.iterdir()
        if f.is_file() and f.suffix.lower() in image_extensions
    ]
    return sorted(images, key=lambda x: x.stat().st_mtime, reverse=True)


def load_image(image_path):
    """Load an image file."""
    try:
        return Image.open(image_path)
    except Exception as e:
        st.error(f"Failed to load image: {e}")
        return None


def main():
    st.set_page_config(page_title="Manual Review - Low Confidence", layout="wide")
    st.title("🔍 Manual Review - Low Confidence Detections")
    st.markdown("Review and correct license plates that the system detected with low confidence.")
    
    # Get images
    images = get_images_in_folder()
    
    if not images:
        st.info("📭 No images to review. All detections have high confidence!")
        st.success("✅ System is working well!")
        return
    
    # Display summary
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Images to Review", len(images))
    with col2:
        st.write("")
        st.write("")
        st.caption("These images need manual verification")
    with col3:
        st.write("")
        st.write("")
        if st.button("🗑️ Clear All", help="Delete all images in the verification folder"):
            for img in images:
                try:
                    img.unlink()
                except Exception as e:
                    st.error(f"Failed to delete {img.name}: {e}")
            st.success("✅ All images cleared!")
            st.rerun()
    
    st.divider()
    
    # Create tabs for browsing and bulk operations
    tab1, tab2 = st.tabs(["📋 Review Images", "🛠️ Bulk Operations"])
    
    # ============================================================
    # TAB 1: Review Individual Images
    # ============================================================
    with tab1:
        st.header("Review Images One by One")
        
        # Image carousel/navigation
        if len(images) > 0:
            # Selection slider
            image_idx = st.slider(
                "Select image to review",
                min_value=0,
                max_value=len(images) - 1,
                value=0,
                format=f"Image %d of {len(images)}"
            )
            
            selected_image = images[image_idx]
            
            # Display image
            col_img, col_info = st.columns([2, 1])
            
            with col_img:
                st.subheader("Detected Image")
                img = load_image(selected_image)
                if img:
                    st.image(img, use_container_width=True)
            
            with col_info:
                st.subheader("📄 Image Details")
                st.write(f"**Filename:** {selected_image.name}")
                st.write(f"**Size:** {selected_image.stat().st_size / 1024:.1f} KB")
                
                # Extract plate text from filename if possible
                filename = selected_image.name
                st.divider()
                st.subheader("🔤 Plate Text")
                
                # Try to extract plate from filename (processed_TIMESTAMP_captured_image.jpg format)
                parts = filename.split("_")
                detected_plate = None
                for part in parts:
                    if part.isupper() or any(c.isdigit() for c in part):
                        detected_plate = part
                        break
                
                # Text input for correction
                corrected_plate = st.text_input(
                    "Correct/Confirm License Plate:",
                    value=detected_plate or "",
                    placeholder="e.g., ABC1234"
                )
                
                # Confidence input
                confidence = st.slider(
                    "Confidence Score:",
                    min_value=0.0,
                    max_value=1.0,
                    value=0.5,
                    step=0.05
                )
                
                st.divider()
                st.subheader("✅ Actions")
                
                col_verify, col_delete = st.columns(2)
                
                with col_verify:
                    if st.button("🔍 Verify Plate", use_container_width=True, type="primary"):
                        if corrected_plate.strip():
                            result = verify_scanned_plate(corrected_plate.strip(), confidence)
                            
                            if result['match_found']:
                                student = result['student_info']
                                st.success("✅ **MATCH FOUND!**")
                                st.write(f"**Student:** {student['name']}")
                                st.write(f"**ID:** {student['student_id']}")
                                st.write(f"**Vehicle:** {student['vehicle_color']}")
                                st.write(f"**Plate:** {student['license_plate']}")
                            else:
                                st.warning("⚠️ **NO MATCH**")
                                st.write(f"Plate '{corrected_plate}' not found in database.")
                                st.info("You can add this student if they are new.")
                        else:
                            st.error("Please enter a license plate.")
                
                with col_delete:
                    if st.button("🗑️ Delete Image", use_container_width=True, type="secondary"):
                        try:
                            selected_image.unlink()
                            st.success("✅ Image deleted.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to delete: {e}")
            
            st.divider()
            
            # Quick student lookup
            st.subheader("👥 Quick Student Lookup")
            students = get_all_students()
            if students:
                st.write("Search student database:")
                col_search1, col_search2 = st.columns(2)
                
                with col_search1:
                    search_term = st.text_input("Search by name or ID:")
                
                with col_search2:
                    color_filter = st.selectbox(
                        "Filter by color:",
                        options=["All"] + sorted(set(s['vehicle_color'] for s in students)),
                        index=0
                    )
                
                # Filter and display
                filtered_students = students
                if search_term.strip():
                    filtered_students = [
                        s for s in filtered_students
                        if search_term.lower() in s['name'].lower() or 
                           search_term.lower() in s['student_id'].lower()
                    ]
                
                if color_filter != "All":
                    filtered_students = [
                        s for s in filtered_students
                        if s['vehicle_color'] == color_filter
                    ]
                
                if filtered_students:
                    df = pd.DataFrame(filtered_students)
                    df = df[['student_id', 'name', 'vehicle_color', 'license_plate']]
                    df.columns = ['ID', 'Name', 'Color', 'Plate']
                    st.dataframe(df, use_container_width=True, hide_index=True, height=150)
                else:
                    st.caption("No students match your search.")
            else:
                st.caption("No students in database yet.")
    
    # ============================================================
    # TAB 2: Bulk Operations
    # ============================================================
    with tab2:
        st.header("Bulk Operations")
        st.markdown("Manage multiple images at once.")
        
        if len(images) > 0:
            st.subheader(f"📊 All {len(images)} Images")
            
            # Display all images as a list
            image_data = []
            for img in images:
                image_data.append({
                    'Filename': img.name,
                    'Size (KB)': f"{img.stat().st_size / 1024:.1f}",
                    'Modified': pd.Timestamp(img.stat().st_mtime, unit='s').strftime('%Y-%m-%d %H:%M:%S')
                })
            
            df_images = pd.DataFrame(image_data)
            st.dataframe(df_images, use_container_width=True, hide_index=True)
            
            st.divider()
            st.subheader("⚙️ Bulk Actions")
            
            col_action1, col_action2 = st.columns(2)
            
            with col_action1:
                st.write("**Delete all images:**")
                if st.button("🗑️ Clear All Images", type="secondary", use_container_width=True):
                    count = 0
                    for img in images:
                        try:
                            img.unlink()
                            count += 1
                        except Exception as e:
                            st.error(f"Failed to delete {img.name}: {e}")
                    st.success(f"✅ Deleted {count} images.")
                    st.rerun()
            
            with col_action2:
                st.write("**Export list:**")
                csv = df_images.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download as CSV",
                    data=csv,
                    file_name="images_to_review.csv",
                    mime="text/csv",
                    use_container_width=True
                )
        else:
            st.info("No images to manage.")
        
        st.divider()
        st.subheader("📝 Statistics")
        col_stat1, col_stat2, col_stat3 = st.columns(3)
        
        with col_stat1:
            st.metric("Total Images", len(images))
        
        with col_stat2:
            if images:
                total_size = sum(img.stat().st_size for img in images) / 1024
                st.metric("Total Size (KB)", f"{total_size:.1f}")
            else:
                st.metric("Total Size (KB)", "0")
        
        with col_stat3:
            st.metric("Status", "✅ All Clear" if len(images) == 0 else f"⚠️ {len(images)} to review")


if __name__ == "__main__":
    main()
