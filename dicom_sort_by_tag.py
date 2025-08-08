# dicom_sort_by_tag.py
import os
import sys
import shutil
import pydicom

# Usage: python dicom_sort_by_tag.py <dicom_folder> <group> <element>
if len(sys.argv) != 4:
    print("Usage: python dicom_sort_by_tag.py <dicom_folder> <group> <element>")
    sys.exit(1)

dicom_folder = sys.argv[1]
group = int(sys.argv[2], 16)
element = int(sys.argv[3], 16)
target_tag = (group, element)

# Output folder to store sorted files
output_root = os.path.join(dicom_folder, "sorted_by_tag")
os.makedirs(output_root, exist_ok=True)

for fname in os.listdir(dicom_folder):
    fpath = os.path.join(dicom_folder, fname)

    # Skip if it's not a file
    if not os.path.isfile(fpath):
        continue

    try:
        ds = pydicom.dcmread(fpath, stop_before_pixels=True)

        if target_tag in ds:
            tag_value = str(ds[target_tag].value)
        else:
            tag_value = "Tag_Not_Found"

        # Create target folder based on tag value
        target_dir = os.path.join(output_root, tag_value)
        os.makedirs(target_dir, exist_ok=True)

        # Move file
        shutil.move(fpath, os.path.join(target_dir, fname))

        print(f"{fname} ! {tag_value}/")

    except Exception as e:
        print(f"Error reading {fname}: {e}")
