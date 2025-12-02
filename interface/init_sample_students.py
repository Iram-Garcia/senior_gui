#!/usr/bin/env python3
"""
Sample script to initialize the student database with example data.
Run this once to populate the students table with test data.
"""
import sys
import os

# Add interface directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from student_db import init_student_db, add_student, get_all_students

def main():
    print("Initializing Student Database...")
    init_student_db()
    
    # Sample student data
    sample_students = [
        ("STU001", "John Doe", "Silver", "ABC1234"),
        ("STU002", "Jane Smith", "Blue", "XYZ9876"),
        ("STU003", "Michael Johnson", "Black", "LMN5555"),
        ("STU004", "Sarah Williams", "Red", "PQR7890"),
        ("STU005", "David Brown", "White", "DEF4321"),
        ("STU006", "Emma Davis", "Gray", "GHI6789"),
    ]
    
    print("\nAdding sample students...")
    for student_id, name, color, plate in sample_students:
        success = add_student(student_id, name, color, plate)
        status = "✓" if success else "✗"
        print(f"{status} {student_id}: {name} ({color} vehicle, LP: {plate})")
    
    print("\nDatabase Summary:")
    students = get_all_students()
    print(f"Total students: {len(students)}")
    
    print("\nStudent List:")
    for student in students:
        print(f"  {student['student_id']:8} | {student['name']:20} | {student['vehicle_color']:10} | {student['license_plate']}")

if __name__ == "__main__":
    main()
