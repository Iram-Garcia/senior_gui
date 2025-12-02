# License Plate Verification System - Integration Guide

## Overview

This is a student license plate verification system that:
1. **Detects** license plates from camera images using YOLO
2. **Reads** the plate numbers using OCR (Optical Character Recognition)
3. **Matches** detected plates against a student database
4. **Logs** all verification attempts for audit and reporting

---

## Database Schema

### `students.db` Tables

#### 1. **students** Table
Stores registered student vehicle information:

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER (PK) | Auto-incrementing primary key |
| student_id | TEXT (UNIQUE) | Student ID (e.g., "STU001") |
| name | TEXT | Student full name |
| vehicle_color | TEXT | Vehicle color (e.g., "Blue", "Red", "Silver") |
| license_plate | TEXT (UNIQUE) | License plate number (e.g., "ABC1234") |
| created_at | TIMESTAMP | Record creation time |
| updated_at | TIMESTAMP | Last update time |

#### 2. **verification_log** Table
Logs all license plate scan attempts:

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER (PK) | Auto-incrementing primary key |
| scanned_plate | TEXT | The plate number detected by OCR |
| student_id | TEXT | Matched student ID (NULL if no match) |
| match_found | BOOLEAN | Whether a match was found (1=yes, 0=no) |
| confidence | REAL | OCR confidence score (0.0-1.0) |
| scan_timestamp | TIMESTAMP | When the scan occurred |

---

## File Structure & Components

```
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

---

## How It Works

### 1. **Registration Phase** (One-time setup)

Students are added to the database via the Streamlit UI (verify.py → "Add Student" tab):

```python
# Manually in UI or programmatically:
from student_db import add_student

add_student(
    student_id="STU001",
    name="John Doe",
    vehicle_color="Silver",
    license_plate="ABC1234"
)
```

### 2. **Detection & Verification Phase** (On each scan)

When a vehicle is detected:

```
Camera/Image → YOLO Detection → OCR Reading → Student Match
                                    ↓
                            ml_processor.py
                            process_image_file()
                                    ↓
                            student_db.verify_scanned_plate()
                                    ↓
                            Returns: match_found, student_info, etc.
```

**In ml_processor.py:**
- YOLO detects the license plate in the image
- OCR reads the text from the detected plate region
- `verify_scanned_plate()` is called automatically
- Result includes whether a student was matched
- Both the scan and result are logged to `verification_log` table

### 3. **Lookup Phase** (Manual verification)

Users can search the database via the verify.py page:

- **Tab 1 - Verify Plate:** Enter a plate manually → see student info if match found
- **Tab 2 - Student Database:** Browse all registered students
- **Tab 3 - Verification History:** View all scan attempts & match results
- **Tab 4 - Add Student:** Register new students with their vehicle info

---

## Getting Started

### Step 1: Initialize the Database

Run the sample data script to create `students.db` with test data:

```bash
cd /workspaces/senior_gui/interface
python init_sample_students.py
```

**Output:**
```
Initializing Student Database...
✓ STU001: John Doe (Silver vehicle, LP: ABC1234)
✓ STU002: Jane Smith (Blue vehicle, LP: XYZ9876)
✓ STU003: Michael Johnson (Black vehicle, LP: LMN5555)
✓ STU004: Sarah Williams (Red vehicle, LP: PQR7890)
✓ STU005: David Brown (White vehicle, LP: DEF4321)
✓ STU006: Emma Davis (Gray vehicle, LP: GHI6789)

Total students: 6
```

### Step 2: Start the Streamlit App

```bash
streamlit run app.py
```

Or from the interface directory:
```bash
cd interface
streamlit run app.py
```

### Step 3: Use the Verification Page

1. Navigate to the **Verification** page (sidebar)
2. Go to **"Add Student"** tab to add more students
3. Go to **"Verify Plate"** tab to test lookup
4. View **"Verification History"** to see all scan logs

---

## Key Functions in `student_db.py`

### `init_student_db()`
- Creates/initializes the SQLite database with the schema
- Called automatically on Streamlit page load

### `add_student(student_id, name, vehicle_color, license_plate) → bool`
- Adds a new student record
- Returns `True` if successful, `False` if student_id or license_plate already exists

### `verify_scanned_plate(scanned_plate, confidence=0.0) → dict`
- Looks up a scanned plate against the database
- Normalizes the plate (uppercase, strips spaces)
- Logs the verification attempt
- Returns a dict with:
  - `match_found`: bool
  - `student_info`: dict or None
  - `scanned_plate`: str
  - `confidence`: float
  - `message`: str

### `lookup_by_license_plate(license_plate) → dict or None`
- Direct lookup for a single license plate
- Returns student dict if found, None otherwise

### `get_all_students() → list[dict]`
- Returns all registered students

### `get_verification_log(limit=100) → list[dict]`
- Returns recent verification attempts (paginated)

### `delete_student(student_id) → bool`
- Removes a student from the database

---

## Integration with ML Processor

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

---

## Example Usage Scenarios

### Scenario 1: Manual Plate Verification

User wants to check if a plate is registered:

```python
from student_db import verify_scanned_plate

result = verify_scanned_plate("ABC1234", confidence=0.92)

if result['match_found']:
    print(f"✓ Found: {result['student_info']['name']}")
else:
    print("✗ No match")
```

### Scenario 2: Add a New Student

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

### Scenario 3: View All Scans for Auditing

```python
from student_db import get_verification_log
import pandas as pd

logs = get_verification_log(limit=50)
df = pd.DataFrame(logs)

# Show matches only
matches = df[df['match_found'] == True]
print(f"Match rate: {len(matches) / len(df) * 100:.1f}%")
```

---

## Notes

- **License Plate Normalization:** Plates are automatically converted to uppercase and spaces are trimmed for matching
- **Confidence Score:** The OCR confidence (0-1) is logged with each verification attempt
- **No Match Handling:** If a plate is detected but not in the database, it's logged as a "no match" event
- **Unique Constraints:** Both `student_id` and `license_plate` must be unique in the database
- **Audit Trail:** All verification attempts (match or not) are logged in `verification_log` for compliance and debugging

---

## Troubleshooting

### Issue: `ModuleNotFoundError: No module named 'student_db'`
**Solution:** Make sure you're running from the `/interface` directory or add it to the Python path.

### Issue: Database is locked
**Solution:** Make sure only one Streamlit instance is running at a time.

### Issue: Plate match not working
**Check:**
1. Is the plate in the database? Use the "Student Database" tab to verify
2. Is the OCR confidence high enough? Check the `confidence` value
3. Are there extra spaces? Plates are normalized but leading/trailing spaces should be handled

### Issue: Want to reset the database
**Solution:** Delete `interface/students.db` and re-run `init_sample_students.py`

---

## Future Enhancements

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
