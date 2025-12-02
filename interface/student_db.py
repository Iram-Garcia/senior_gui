"""
Student Database Module
Manages the SQLite database for student records with license plate info.
"""
import sqlite3
import os
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# Database file location
INTERFACE_DIR = os.path.dirname(os.path.abspath(__file__))
STUDENTS_DB = os.path.join(INTERFACE_DIR, 'students.db')


def init_student_db():
    """Initialize the student database with the required schema."""
    conn = sqlite3.connect(STUDENTS_DB)
    cursor = conn.cursor()
    
    # Create students table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        vehicle_color TEXT,
        license_plate TEXT UNIQUE NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create a verification log table to track scans
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS verification_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        scanned_plate TEXT NOT NULL,
        student_id TEXT,
        match_found BOOLEAN NOT NULL,
        confidence REAL,
        scan_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    conn.commit()
    conn.close()
    logger.info(f"Student database initialized at {STUDENTS_DB}")


def add_student(student_id: str, name: str, vehicle_color: str, license_plate: str) -> bool:
    """
    Add a new student to the database.
    
    Args:
        student_id: Student ID (unique)
        name: Student name
        vehicle_color: Vehicle color (e.g., "Red", "Blue", "Silver")
        license_plate: License plate number (unique)
    
    Returns:
        True if successful, False otherwise
    """
    try:
        conn = sqlite3.connect(STUDENTS_DB)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO students (student_id, name, vehicle_color, license_plate)
        VALUES (?, ?, ?, ?)
        ''', (student_id, name, vehicle_color, license_plate))
        
        conn.commit()
        conn.close()
        logger.info(f"Added student {student_id}: {name} with LP {license_plate}")
        return True
    except sqlite3.IntegrityError as e:
        logger.error(f"Integrity error adding student: {e}")
        return False
    except Exception as e:
        logger.error(f"Error adding student: {e}")
        return False


def lookup_by_license_plate(license_plate: str) -> Optional[Dict[str, Any]]:
    """
    Look up a student by license plate.
    
    Args:
        license_plate: The license plate to search for
    
    Returns:
        Dict with student info if found, None otherwise
    """
    try:
        conn = sqlite3.connect(STUDENTS_DB)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT id, student_id, name, vehicle_color, license_plate
        FROM students
        WHERE license_plate = ?
        ''', (license_plate,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    except Exception as e:
        logger.error(f"Error looking up license plate: {e}")
        return None


def verify_scanned_plate(scanned_plate: str, confidence: float = 0.0) -> Dict[str, Any]:
    """
    Verify a scanned license plate against the database.
    
    Args:
        scanned_plate: The OCR-detected license plate text
        confidence: Confidence score from OCR (0-1)
    
    Returns:
        Dict with verification result:
        {
            'match_found': bool,
            'student_info': dict or None,
            'scanned_plate': str,
            'confidence': float,
            'message': str
        }
    """
    result = {
        'match_found': False,
        'student_info': None,
        'scanned_plate': scanned_plate,
        'confidence': confidence,
        'message': ''
    }
    
    # Normalize plate (remove spaces, convert to uppercase)
    normalized_plate = scanned_plate.strip().upper()
    
    student = lookup_by_license_plate(normalized_plate)
    
    if student:
        result['match_found'] = True
        result['student_info'] = student
        result['message'] = f"✓ Match found: {student['name']} ({student['student_id']})"
    else:
        result['match_found'] = False
        result['message'] = f"✗ No student found with license plate: {normalized_plate}"
    
    # Log verification attempt
    try:
        conn = sqlite3.connect(STUDENTS_DB)
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO verification_log (scanned_plate, student_id, match_found, confidence)
        VALUES (?, ?, ?, ?)
        ''', (
            normalized_plate,
            student['student_id'] if student else None,
            result['match_found'],
            confidence
        ))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Error logging verification: {e}")
    
    return result


def get_all_students() -> List[Dict[str, Any]]:
    """Get all students from the database."""
    try:
        conn = sqlite3.connect(STUDENTS_DB)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT id, student_id, name, vehicle_color, license_plate FROM students ORDER BY name')
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Error fetching all students: {e}")
        return []


def delete_student(student_id: str) -> bool:
    """Delete a student by student ID."""
    try:
        conn = sqlite3.connect(STUDENTS_DB)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM students WHERE student_id = ?', (student_id,))
        conn.commit()
        conn.close()
        
        logger.info(f"Deleted student {student_id}")
        return True
    except Exception as e:
        logger.error(f"Error deleting student: {e}")
        return False


def get_verification_log(limit: int = 100) -> List[Dict[str, Any]]:
    """Get recent verification attempts."""
    try:
        conn = sqlite3.connect(STUDENTS_DB)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT id, scanned_plate, student_id, match_found, confidence, scan_timestamp
        FROM verification_log
        ORDER BY scan_timestamp DESC
        LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Error fetching verification log: {e}")
        return []
