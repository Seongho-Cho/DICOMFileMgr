# count_dicoms_by_folder.py
import os
import sys
import pydicom

# How to run: python count_dicoms_by_folder.py <parent_folder>
if len(sys.argv) != 2:
    print("Usage: python count_dicoms_by_folder.py <parent_folder>")
    sys.exit(1)

parent_folder = sys.argv[1]

if not os.path.isdir(parent_folder):
    print(f"! Path not found: {parent_folder}")
    sys.exit(1)

folder_counts = {}

# Traverse immediate subfolders under the parent folder
for folder_name in os.listdir(parent_folder):
    folder_path = os.path.join(parent_folder, folder_name)
    if os.path.isdir(folder_path):
        count = 0
        for file_name in os.listdir(folder_path):
            file_path = os.path.join(folder_path, file_name)
            if os.path.isfile(file_path):
                try:
                    # Use stop_before_pixels=True for speed optimization
                    ds = pydicom.dcmread(file_path, stop_before_pixels=True)
                    count += 1
                except:
                    pass  # Ignore if not a DICOM file
        folder_counts[folder_name] = count

# Print results sorted by count descending
for folder, count in sorted(folder_counts.items(), key=lambda x: x[1], reverse=True):
    print(f"{folder}: {count} DICOM files")
