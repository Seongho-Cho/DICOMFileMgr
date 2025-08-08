import os
import sys
import pydicom
from collections import defaultdict

# How to run: python dicom_counter_by_tag.py /path/to/dicom/folder 0008 0050
if len(sys.argv) != 4:
    print("Usage: python dicom_counter_by_tag.py <dicom_folder> <group> <element>")
    sys.exit(1)

# Get folder path first
dicom_folder = sys.argv[1]

# Convert group and element to hexadecimal integers
group = int(sys.argv[2], 16)
element = int(sys.argv[3], 16)
target_tag = (group, element)

tag_value_counts = defaultdict(int)

# Traverse all subdirectories
for root, dirs, files in os.walk(dicom_folder):
    for fname in files:
        fpath = os.path.join(root, fname)
        try:
            ds = pydicom.dcmread(fpath, stop_before_pixels=True)
            if target_tag in ds:
                value = str(ds[target_tag].value)
            else:
                value = "Tag Not Found"
            tag_value_counts[value] += 1
        except Exception as e:
            print(f"Error reading {fname}: {e}")

# Print results
for val, count in tag_value_counts.items():
    print(f"Tag Value: {val}, File Count: {count}")
