"""
Verification & Lookup Page
Allows searching for students by license plate and viewing verification history.
"""
import streamlit as st
import pandas as pd
from student_db import (
    init_student_db, 
    verify_scanned_plate, 
    get_all_students,
    get_verification_log,
    add_student,
    delete_student
)

# Initialize DB on page load
init_student_db()


def main():
    st.set_page_config(page_title="License Plate Verification", layout="wide")
    
    st.title("🚗 License Plate Verification & Student Database")
    
    # Create tabs for different sections
    tab1, tab2, tab3, tab4 = st.tabs([
        "🔍 Verify Plate",
        "👥 Student Database",
        "📋 Verification History",
        "➕ Add Student"
    ])
    
    # ============================================================
    # TAB 1: Verify a Scanned License Plate
    # ============================================================
    with tab1:
        st.header("Verify Scanned License Plate")
        st.markdown("Enter the license plate detected by the system to check if the student is registered.")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            scanned_plate = st.text_input(
                "Enter License Plate",
                placeholder="e.g., ABC1234 or TX-123-45",
                help="Enter the license plate as detected by the OCR system"
            )
            confidence = st.slider(
                "OCR Confidence Score",
                min_value=0.0,
                max_value=1.0,
                value=0.85,
                step=0.05,
                help="Confidence of the OCR detection (0=low, 1=high)"
            )
        
        with col2:
            st.write("")  # Spacing
            st.write("")
            if st.button("🔍 Verify", use_container_width=True, type="primary"):
                if scanned_plate.strip():
                    result = verify_scanned_plate(scanned_plate, confidence)
                    
                    if result['match_found']:
                        st.success("✅ **MATCH FOUND!**")
                        student = result['student_info']
                        
                        # Display student info in a nice card-like format
                        col_info1, col_info2 = st.columns(2)
                        with col_info1:
                            st.metric("Student ID", student['student_id'])
                            st.metric("Name", student['name'])
                        with col_info2:
                            st.metric("Vehicle Color", student['vehicle_color'])
                            st.metric("License Plate", student['license_plate'])
                        
                        st.metric("Detection Confidence", f"{confidence:.1%}")
                    else:
                        st.warning("⚠️ **NO MATCH**")
                        st.write(f"**Scanned Plate:** {scanned_plate}")
                        st.write(f"**Confidence:** {confidence:.1%}")
                        st.info("This license plate is not registered in the student database.")
                else:
                    st.error("Please enter a license plate number.")
        
        st.divider()
        st.subheader("📊 Quick Stats")
        students = get_all_students()
        st.metric("Total Registered Students", len(students))
    
    # ============================================================
    # TAB 2: Student Database Browser
    # ============================================================
    with tab2:
        st.header("Student Database")
        st.markdown("View and manage student records with license plate information.")
        
        students = get_all_students()
        
        if students:
            # Convert to DataFrame for nice display
            df = pd.DataFrame(students)
            df = df[['student_id', 'name', 'vehicle_color', 'license_plate']]
            df.columns = ['Student ID', 'Name', 'Vehicle Color', 'License Plate']
            
            # Display as editable data editor (read-only preview if Streamlit version doesn't support editing)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            # Export CSV
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download as CSV",
                data=csv,
                file_name="students.csv",
                mime="text/csv"
            )
            
            # Delete student section
            st.subheader("🗑️ Remove Student")
            cols = st.columns([2, 1])
            with cols[0]:
                student_to_delete = st.selectbox(
                    "Select a student to remove:",
                    options=[f"{s['student_id']} - {s['name']}" for s in students],
                    key="delete_select"
                )
            with cols[1]:
                if st.button("Delete", type="secondary"):
                    student_id = student_to_delete.split(" - ")[0]
                    if delete_student(student_id):
                        st.success(f"Deleted student {student_id}")
                        st.rerun()
                    else:
                        st.error("Failed to delete student")
        else:
            st.info("No students in database yet. Add one in the 'Add Student' tab.")
    
    # ============================================================
    # TAB 3: Verification History
    # ============================================================
    with tab3:
        st.header("Verification History")
        st.markdown("View recent license plate verification attempts.")
        
        log_entries = get_verification_log(limit=100)
        
        if log_entries:
            df_log = pd.DataFrame(log_entries)
            df_log = df_log[[
                'scanned_plate', 'student_id', 'match_found', 'confidence', 'scan_timestamp'
            ]]
            df_log.columns = [
                'Scanned Plate', 'Student ID', 'Match Found', 'Confidence', 'Timestamp'
            ]
            
            # Color code the match_found column
            def color_match(val):
                return 'background-color: #90EE90' if val else 'background-color: #FFB6C1'
            
            st.dataframe(
                df_log.style.applymap(color_match, subset=['Match Found']),
                use_container_width=True,
                hide_index=True
            )
            
            # Statistics
            col_stat1, col_stat2, col_stat3 = st.columns(3)
            total = len(log_entries)
            matches = sum(1 for e in log_entries if e['match_found'])
            
            with col_stat1:
                st.metric("Total Scans", total)
            with col_stat2:
                st.metric("Matches Found", matches)
            with col_stat3:
                match_rate = (matches / total * 100) if total > 0 else 0
                st.metric("Match Rate", f"{match_rate:.1f}%")
        else:
            st.info("No verification history yet.")
    
    # ============================================================
    # TAB 4: Add New Student
    # ============================================================
    with tab4:
        st.header("Add New Student")
        st.markdown("Register a new student with their vehicle and license plate information.")
        
        with st.form("add_student_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                student_id = st.text_input(
                    "Student ID",
                    placeholder="e.g., STU001",
                    help="Unique identifier for the student"
                )
                name = st.text_input(
                    "Student Name",
                    placeholder="e.g., John Doe",
                    help="Full name of the student"
                )
            
            with col2:
                vehicle_color = st.selectbox(
                    "Vehicle Color",
                    options=[
                        "Red", "Blue", "Silver", "Black", "White", "Gray",
                        "Green", "Yellow", "Orange", "Purple", "Brown", "Other"
                    ],
                    help="Color of the student's vehicle"
                )
                license_plate = st.text_input(
                    "License Plate",
                    placeholder="e.g., ABC1234",
                    help="License plate number (must be unique)"
                )
            
            # Submit button
            submitted = st.form_submit_button("✅ Add Student", use_container_width=True, type="primary")
            
            if submitted:
                # Validation
                if not student_id or not name or not license_plate:
                    st.error("Please fill in all required fields.")
                elif len(student_id.strip()) == 0:
                    st.error("Student ID cannot be empty.")
                elif len(name.strip()) == 0:
                    st.error("Name cannot be empty.")
                elif len(license_plate.strip()) == 0:
                    st.error("License plate cannot be empty.")
                else:
                    # Add to database
                    if add_student(student_id, name, vehicle_color, license_plate):
                        st.success(f"✅ Student {name} ({student_id}) added successfully!")
                        st.info(f"License Plate: {license_plate} | Vehicle: {vehicle_color}")
                        # Clear form by rerunning
                        st.rerun()
                    else:
                        st.error("Failed to add student. The Student ID or License Plate may already exist.")
        
        # Show existing students as reference
        st.divider()
        st.subheader("📋 Current Students (for reference)")
        students = get_all_students()
        if students:
            df = pd.DataFrame(students)
            df = df[['student_id', 'name', 'license_plate']]
            st.dataframe(df, use_container_width=True, hide_index=True, height=200)
        else:
            st.caption("No students registered yet.")


if __name__ == "__main__":
    main()
