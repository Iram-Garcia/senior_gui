# Senior GUI - License Plate Verification System

## Overview

This repository contains two main parts that require separate Python virtual environments:

- **interface** (Streamlit front-end with license plate verification)
- **ml** (machine learning code)

The system provides a complete license plate verification solution that detects plates from vehicle images, reads them via OCR, and matches them against a student database for automated verification and logging.

---

## Prerequisites

- Python 3.8+ installed and on your PATH.
- Optional but recommended: upgrade pip:

  ```sh
  python -m pip install --upgrade pip
  ```

---

## Creating and Using Virtual Environments

General notes:

- Use distinct environments for `interface` and `ml`.
- Recommended naming: `.venv_interface` and `.venv_ml` (dot-prefixed keeps them hidden on Unix-like systems).

### 1. Interface Environment

- Open a terminal and navigate to the interface folder:

     ```sh
     cd interface
     ```

   -Create the venv:

  ```sh
     python -m venv .venv_interface
     ```

-Activate the environment:

  -Windows Command Prompt (cmd.exe):

  ```sh
       .venv_interface\Scripts\activate
       ```

     -Windows PowerShell:

       ```powershell
       .\.venv_interface\Scripts\Activate.ps1
       ```

      -macOS / Linux (bash / zsh):

       ```sh
       source .venv_interface/bin/activate
       ```

-Install dependencies:

     ```sh
     pip install -r requirements.txt
     ```

### 2. ML Environment

-Open a new terminal and navigate to the ml folder:

  ```sh
     cd ml
  ```

-Create the venv:

  ```sh
     python -m venv .venv_ml
  ```

- Activate the environment (same variants as above, substituting `.venv_ml`).
- Install dependencies:

     ```sh
     pip install -r requirements.txt
     ```

---

## Quick Setup (5 minutes)

### Step 1: Initialize Database with Sample Data

```bash
cd interface
python init_sample_students.py
```

Expected output:

```bash
✓ STU001: John Doe (Silver vehicle, LP: ABC1234)
✓ STU002: Jane Smith (Blue vehicle, LP: XYZ9876)
... (6 sample students added)
```

### Step 2: Start Streamlit App

```bash
streamlit run app.py
```

### Step 3: Open Browser

- Default URL: `http://localhost:8501`
- Navigate to **Verification** page (in sidebar)

---

## What You Can Do Now

### 1. **Verify a License Plate** (Manual)

- Go to **Verification** → **🔍 Verify Plate** tab
- Enter a plate: `ABC1234`, `XYZ9876`, etc.
- See student details if matched ✓

### 2. **Add a New Student**

- Go to **Verification** → **➕ Add Student** tab
- Fill in: Student ID, Name, Vehicle Color, License Plate
- Click "Add Student"

### 3. **Browse All Students**

- Go to **Verification** → **👥 Student Database** tab
- View all registered students
- Export as CSV
- Delete students

### 4. **View Verification History**

- Go to **Verification** → **📋 Verification History** tab
- See all scan attempts (matches and non-matches)
- View statistics (match rate, etc.)

---

## How It Works (Behind the Scenes)

### When a Vehicle is Scanned

```bash
1. Camera captures image
   ↓
2. YOLO detects license plate region
   ↓
3. OCR reads plate text + confidence
   ↓
4. verify_scanned_plate() is called automatically
   ↓
5. Database lookup for student match
   ↓
6. Result logged to verification_log table
   ↓
7. Scan result (match/no match) returned to UI
```

The `student_match` result is automatically included in the processing pipeline output.

---

## Database Schema

### `students` Table

```bash
student_id (unique)  | name              | vehicle_color | license_plate (unique)
STU001              | John Doe          | Silver        | ABC1234
STU002              | Jane Smith        | Blue          | XYZ9876
...
```

### `verification_log` Table

```bash

scanned_plate | student_id | match_found | confidence | scan_timestamp
ABC1234      | STU001     | 1           | 0.95       | 2024-12-02 14:30:00
UNKNOWN99    | NULL       | 0           | 0.85       | 2024-12-02 14:31:00
...
```

---

## Sample Data Included

6 pre-loaded students for testing:

| Student ID | Name | Vehicle | License Plate |
|-----------|------|---------|---------------|
| STU001 | John Doe | Silver | ABC1234 |
| STU002 | Jane Smith | Blue | XYZ9876 |
| STU003 | Michael Johnson | Black | LMN5555 |
| STU004 | Sarah Williams | Red | PQR7890 |
| STU005 | David Brown | White | DEF4321 |
| STU006 | Emma Davis | Gray | GHI6789 |

**Try these plates in the "Verify Plate" tab to test!**

---

## Files Created/Modified

### New Filesb

1. **`student_db.py`** - Database module for student records and verification
2. **`pages/verify.py`** - Completely revamped with 4-tab verification interface
3. **`init_sample_students.py`** - Script to populate sample student data
4. **`LP_VERIFICATION_GUIDE.md`** - Comprehensive technical documentation

### Modified Files

1. **`ml_processor.py`** - Added automatic student verification on plate detection

### Databases Created

1. **`students.db`** - New SQLite database with student records and verification logs

---

## Python API Reference

### Import and Use

```python
from student_db import verify_scanned_plate, add_student, get_all_students

# Verify a plate
result = verify_scanned_plate("ABC1234", confidence=0.95)
if result['match_found']:
    print(f"Found: {result['student_info']['name']}")

# Add a student
add_student("STU007", "Alice Johnson", "Green", "QWE4567")

# Get all students
students = get_all_students()
for s in students:
    print(f"{s['student_id']}: {s['name']}")
```

---

## Testing

### Test Scenario 1: Verify Known Plate

```bash
Input:  "ABC1234"
Output: ✓ Match found: John Doe (STU001)
```

### Test Scenario 2: Verify Unknown Plate

```bash
Input:  "UNKNOWN99"
Output: ✗ No student found with license plate: UNKNOWN99
```

### Test Scenario 3: Add New Student

```bash
Student ID: STU007
Name: Alice Johnson
Color: Green
Plate: QWE4567
→ Successfully added
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError: student_db` | Run from `/interface` directory |
| Database locked | Close other Streamlit instances |
| Plate not matching | Check spelling, it's case-insensitive but spaces matter |
| No data in database | Run `python init_sample_students.py` |

---

## Reset Database

To start fresh:

```bash

cd interface
rm students.db
python init_sample_students.py
```

---

## Key Features

 **Real-time verification** - Automatic matching during scanning  
 **Audit trail** - All verification attempts logged  
 **Easy management** - Add/remove students via UI  
 **Search & history** - Browse students and verification logs  
 **CSV export** - Download student list or logs  
 **Confidence scoring** - OCR confidence tracked with each scan  
 **No-match handling** - Logs unknown plates for investigation  

---

## Next Steps

1. **Add real student data** using the UI or programmatically
2. **Test with your camera/images** - the system will auto-verify plates
3. **View verification logs** for auditing and reporting
4. **Customize** as needed (add more fields, change colors, etc.)

---

## Detailed Integration Guide

### File Structure & Components

```bash
interface/
├── student_db.py                  # Database module (NEW)
├── ml_processor.py               # Updated with student verification
├── pages/
│   └── verify.py                # Updated verification & lookup page (NEW)
├── init_sample_students.py       # Script to populate sample data (NEW)
├── students.db                   # SQLite database (created on first run)
├── license_plate_results.txt     # Log file (existing)
└── data.db                       # Existing database (for page 1)
```

### Key Functions in `student_db.py`

#### `init_student_db()`

- Creates/initializes the SQLite database with the schema
- Called automatically on Streamlit page load

#### `add_student(student_id, name, vehicle_color, license_plate) → bool`

- Adds a new student record
- Returns `True` if successful, `False` if student_id or license_plate already exists

#### `verify_scanned_plate(scanned_plate, confidence=0.0) → dict`

- Looks up a scanned plate against the database
- Normalizes the plate (uppercase, strips spaces)
- Logs the verification attempt
- Returns a dict with:
  - `match_found`: bool
  - `student_info`: dict or None
  - `scanned_plate`: str
  - `confidence`: float
  - `message`: str

#### `lookup_by_license_plate(license_plate) → dict or None`

- Direct lookup for a single license plate
- Returns student dict if found, None otherwise

#### `get_all_students() → list[dict]`

- Returns all registered students

#### `get_verification_log(limit=100) → list[dict]`

- Returns recent verification attempts (paginated)

#### `delete_student(student_id) → bool`

- Removes a student from the database

### Integration with ML Processor

The `ml_processor.py` automatically calls the verification function when a plate is detected:

```python
# In ml_processor.py, process_image_file() method:

if _STUDENT_DB_AVAILABLE and text != "No plate detected":
    try:
        student_match = verify_scanned_plate(text, float(confidence))
    except Exception as e:
        logger.error(f"Student verification error: {e}")

# The return dict now includes:
return {
    ...
    'student_match': student_match,  # Verification result
}
```

**Return value example:**

```python
{
    'image_file_name': 'captured_image.jpg',
    'text': 'ABC1234',
    'confidence': 0.95,
    'execution_time_s': 0.42,
    'student_match': {
        'match_found': True,
        'student_info': {
            'id': 1,
            'student_id': 'STU001',
            'name': 'John Doe',
            'vehicle_color': 'Silver',
            'license_plate': 'ABC1234'
        },
        'scanned_plate': 'ABC1234',
        'confidence': 0.95,
        'message': '✓ Match found: John Doe (STU001)'
    }
}
```

### Example Usage Scenarios

#### Scenario 1: Manual Plate Verification

```python
from student_db import verify_scanned_plate

result = verify_scanned_plate("ABC1234", confidence=0.92)

if result['match_found']:
    print(f"✓ Found: {result['student_info']['name']}")
else:
    print("✗ No match")
```

#### Scenario 2: Add a New Student

```python
from student_db import add_student

success = add_student(
    student_id="STU007",
    name="Alice Johnson",
    vehicle_color="Green",
    license_plate="QWE4567"
)

if success:
    print("Student registered!")
else:
    print("Failed - ID or LP may already exist")
```

#### Scenario 3: View All Scans for Auditing

```python
from student_db import get_verification_log
import pandas as pd

logs = get_verification_log(limit=50)
df = pd.DataFrame(logs)

# Show matches only
matches = df[df['match_found'] == True]
print(f"Match rate: {len(matches) / len(df) * 100:.1f}%")
```

### Notes

- **License Plate Normalization:** Plates are automatically converted to uppercase and spaces are trimmed for matching
- **Confidence Score:** The OCR confidence (0-1) is logged with each verification attempt
- **No Match Handling:** If a plate is detected but not in the database, it's logged as a "no match" event
- **Unique Constraints:** Both `student_id` and `license_plate` must be unique in the database
- **Audit Trail:** All verification attempts (match or not) are logged in `verification_log` for compliance and debugging

### Future Enhancements

Possible improvements:

- [ ] Fuzzy matching for OCR errors (e.g., "1" misread as "I")
- [ ] Photo capture of matched students for audit trail
- [ ] SMS/Email notifications on unauthorized plates
- [ ] Analytics dashboard (peak hours, frequent visitors, etc.)
- [ ] Integration with access control systems
- [ ] Bulk import from CSV for student registration

---

## Contact & Support

For issues or questions, refer to:

- `student_db.py` - Database module documentation
- `ml_processor.py` - ML processing and integration
- `pages/verify.py` - UI and user-facing functions
