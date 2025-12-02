"""
Page 1: Student Database Management
View, add, and edit student records with their vehicle information.
"""
import streamlit as st
import pandas as pd
from student_db import (
    init_student_db,
    add_student,
    get_all_students,
    delete_student,
)

# Initialize database on page load
init_student_db()


def main():
    st.set_page_config(page_title="Student Database Management", layout="wide")
    st.title("👥 Student Database Management")
    st.markdown("View, add, edit, and manage student vehicle records.")
    
    # Create tabs for different sections
    tab1, tab2, tab3 = st.tabs(["📊 View Students", "➕ Add Student", "🗑️ Remove Student"])
    
    # ============================================================
    # TAB 1: View All Students
    # ============================================================
    with tab1:
        st.header("Student Records")
        students = get_all_students()
        
        if students:
            # Convert to DataFrame for nice display
            df = pd.DataFrame(students)
            df = df[['student_id', 'name', 'vehicle_color', 'license_plate']]
            df.columns = ['Student ID', 'Name', 'Vehicle Color', 'License Plate']
            
            # Display with sorting/filtering
            st.subheader(f"Total Students: {len(students)}")
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            # Statistics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Registered", len(students))
            with col2:
                colors = df['Vehicle Color'].unique()
                st.metric("Unique Vehicle Colors", len(colors))
            with col3:
                st.metric("License Plates", len(df))
            
            # Export options
            st.divider()
            st.subheader("📥 Export Options")
            
            col_csv, col_json = st.columns(2)
            
            with col_csv:
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download as CSV",
                    data=csv,
                    file_name="students.csv",
                    mime="text/csv"
                )
            
            with col_json:
                import json
                json_data = json.dumps(students, indent=2, default=str).encode('utf-8')
                st.download_button(
                    label="Download as JSON",
                    data=json_data,
                    file_name="students.json",
                    mime="application/json"
                )
            
            # Search/filter
            st.divider()
            st.subheader("🔍 Search Students")
            
            search_col1, search_col2 = st.columns(2)
            
            with search_col1:
                search_term = st.text_input("Search by name or ID:", placeholder="e.g., John or STU001")
            
            with search_col2:
                color_filter = st.selectbox(
                    "Filter by vehicle color:",
                    options=["All Colors"] + sorted(list(colors)),
                    index=0
                )
            
            # Filter results
            filtered_df = df.copy()
            
            if search_term.strip():
                filtered_df = filtered_df[
                    (filtered_df['Name'].str.contains(search_term, case=False, na=False)) |
                    (filtered_df['Student ID'].str.contains(search_term, case=False, na=False))
                ]
            
            if color_filter != "All Colors":
                filtered_df = filtered_df[filtered_df['Vehicle Color'] == color_filter]
            
            if len(filtered_df) > 0:
                st.subheader(f"Search Results: {len(filtered_df)} found")
                st.dataframe(filtered_df, use_container_width=True, hide_index=True)
            elif search_term.strip() or color_filter != "All Colors":
                st.warning("No students match your search criteria.")
        
        else:
            st.info("📭 No students in the database yet. Go to the 'Add Student' tab to register students.")
    
    # ============================================================
    # TAB 2: Add New Student
    # ============================================================
    with tab2:
        st.header("Register New Student")
        st.markdown("Add a new student to the database with their vehicle information.")
        
        with st.form("add_student_form", border=True):
            col1, col2 = st.columns(2)
            
            with col1:
                student_id = st.text_input(
                    "Student ID *",
                    placeholder="e.g., STU001",
                    help="Unique identifier for the student"
                )
                name = st.text_input(
                    "Student Name *",
                    placeholder="e.g., John Doe",
                    help="Full name of the student"
                )
            
            with col2:
                vehicle_color = st.selectbox(
                    "Vehicle Color *",
                    options=[
                        "Red", "Blue", "Silver", "Black", "White", "Gray",
                        "Green", "Yellow", "Orange", "Purple", "Brown", "Other"
                    ],
                    help="Color of the student's vehicle"
                )
                license_plate = st.text_input(
                    "License Plate *",
                    placeholder="e.g., ABC1234",
                    help="License plate number (must be unique)"
                )
            
            st.markdown("---")
            st.caption("* Required fields")
            
            # Submit button
            submitted = st.form_submit_button("✅ Add Student", use_container_width=True, type="primary")
            
            if submitted:
                # Validation
                if not student_id.strip() or not name.strip() or not license_plate.strip():
                    st.error("❌ Please fill in all required fields (marked with *).")
                else:
                    # Add to database
                    if add_student(student_id.strip(), name.strip(), vehicle_color, license_plate.strip()):
                        st.success(f"✅ Student Added Successfully!")
                        st.balloons()
                        st.write(f"**{name}** ({student_id})")
                        st.write(f"�� Vehicle: {vehicle_color} | 📋 License Plate: {license_plate}")
                        st.info("The student has been registered in the database.")
                    else:
                        st.error("❌ Failed to add student. The Student ID or License Plate may already exist.")
                        st.warning("Please use unique values for Student ID and License Plate.")
        
        # Show current students as reference
        st.divider()
        st.subheader("📋 Current Students (for reference)")
        current_students = get_all_students()
        if current_students:
            df_ref = pd.DataFrame(current_students)
            df_ref = df_ref[['student_id', 'name', 'license_plate']]
            df_ref.columns = ['ID', 'Name', 'License Plate']
            st.dataframe(df_ref, use_container_width=True, hide_index=True, height=250)
            st.caption(f"Total: {len(current_students)} students")
        else:
            st.caption("No students registered yet.")
    
    # ============================================================
    # TAB 3: Remove Student
    # ============================================================
    with tab3:
        st.header("Remove Student")
        st.markdown("⚠️ Remove a student from the database. This action cannot be undone.")
        
        students = get_all_students()
        
        if students:
            # Create display text with both ID and name
            student_options = [f"{s['student_id']} — {s['name']}" for s in students]
            
            col_select, col_button = st.columns([3, 1])
            
            with col_select:
                selected = st.selectbox(
                    "Select a student to remove:",
                    options=student_options,
                    format_func=lambda x: x,
                    key="delete_select"
                )
            
            if selected:
                # Extract student ID from selection
                student_id = selected.split(" — ")[0]
                selected_student = next((s for s in students if s['student_id'] == student_id), None)
                
                # Show details of student being deleted
                st.divider()
                st.subheader("🗂️ Student to be removed:")
                col_info1, col_info2 = st.columns(2)
                with col_info1:
                    st.write(f"**Student ID:** {selected_student['student_id']}")
                    st.write(f"**Name:** {selected_student['name']}")
                with col_info2:
                    st.write(f"**Vehicle Color:** {selected_student['vehicle_color']}")
                    st.write(f"**License Plate:** {selected_student['license_plate']}")
                
                # Confirmation checkbox
                st.divider()
                confirm = st.checkbox(
                    "⚠️ I understand this action cannot be undone. Delete this student?",
                    value=False
                )
                
                col_delete, col_cancel = st.columns(2)
                with col_delete:
                    if st.button("🗑️ Delete Student", type="secondary", use_container_width=True, disabled=not confirm):
                        if delete_student(student_id):
                            st.success(f"✅ Student {selected_student['name']} ({student_id}) has been deleted.")
                            st.info("The database has been updated.")
                            st.rerun()
                        else:
                            st.error(f"❌ Failed to delete student {student_id}.")
        else:
            st.info("📭 No students in the database to delete.")


if __name__ == "__main__":
    main()
