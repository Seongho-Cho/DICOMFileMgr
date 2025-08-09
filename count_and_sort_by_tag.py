import os
import sys
import pydicom
import shutil

# How to run:
# python count_and_sort_by_tag.py <parent_folder> <tag_group> <tag_element>
# Example: python count_and_sort_by_tag.py ./DICOMs 0x0010 0x0020

if len(sys.argv) != 4:
    print("Usage: python count_and_sort_by_tag.py <parent_folder> <tag_group> <tag_element>")
    sys.exit(1)

parent_folder = sys.argv[1]
tag_group = int(sys.argv[2], 16)
tag_element = int(sys.argv[3], 16)

if not os.path.isdir(parent_folder):
    print(f"! Cannot find path: {parent_folder}")
    sys.exit(1)

folder_counts = {}

# Count DICOM files by tag value
for folder_name in os.listdir(parent_folder):
    folder_path = os.path.join(parent_folder, folder_name)
    if os.path.isdir(folder_path):
        count = 0
        for file_name in os.listdir(folder_path):
            file_path = os.path.join(folder_path, file_name)
            if os.path.isfile(file_path):
                try:
                    ds = pydicom.dcmread(file_path, stop_before_pixels=True)
                    tag_value = str(ds.get((tag_group, tag_element), ""))
                    if tag_value.strip():
                        count += 1
                except:
                    pass
        folder_counts[folder_name] = count

# Show result
print("\n=== Count Result by Folder ===")
for folder, count in sorted(folder_counts.items(), key=lambda x: x[1], reverse=True):
    print(f"{folder}: {count} DICOM files")

# Ask user if they want to sort
while True:
    user_input = input("\nDo you want to sort files into folders by tag value? (Y/N): ").strip().lower()
    if user_input in ["y", "yes"]:
        sort_confirmed = True
        break
    elif user_input in ["n", "no"]:
        sort_confirmed = False
        break
    else:
        print("! Please enter Y or N (yes/no)")

# Sort and move files
if sort_confirmed:
    print("Sorting files by tag value...")
    for folder_name in os.listdir(parent_folder):
        folder_path = os.path.join(parent_folder, folder_name)
        if os.path.isdir(folder_path):
            for file_name in os.listdir(folder_path):
                file_path = os.path.join(folder_path, file_name)
                if os.path.isfile(file_path):
                    try:
                        ds = pydicom.dcmread(file_path, stop_before_pixels=True)
                        tag_value = str(ds.get((tag_group, tag_element), "Unknown"))
                        dest_folder = os.path.join(parent_folder, tag_value)
                        os.makedirs(dest_folder, exist_ok=True)
                        shutil.move(file_path, os.path.join(dest_folder, file_name))
                    except:
                        pass
    print("! Sorting completed")
else:
    print("! Sorting canceled")
