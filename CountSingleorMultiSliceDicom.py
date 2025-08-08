import os
import sys
import pydicom
from collections import defaultdict

# How to run: python count_multi_single.py <parent_folder>
if len(sys.argv) != 2:
    print("Usage: python count_multi_single.py <parent_folder>")
    sys.exit(1)

parent_folder = sys.argv[1]

if not os.path.isdir(parent_folder):
    print(f"! Folder not found: {parent_folder}")
    sys.exit(1)

# Store results for each folder
results = defaultdict(lambda: {"multi": 0, "single": 0, "unknown": 0})

for folder_name in os.listdir(parent_folder):
    folder_path = os.path.join(parent_folder, folder_name)
    if not os.path.isdir(folder_path):
        continue

    for fname in os.listdir(folder_path):
        fpath = os.path.join(folder_path, fname)
        if not os.path.isfile(fpath):
            continue
        try:
            ds = pydicom.dcmread(fpath, stop_before_pixels=True, force=True)
            num_frames_tag = ds.get((0x0028, 0x0008), None)  # Number of Frames
            if num_frames_tag:
                try:
                    num_frames = int(str(num_frames_tag.value))
                    if num_frames > 1:
                        results[folder_name]["multi"] += 1
                    else:
                        results[folder_name]["single"] += 1
                except:
                    results[folder_name]["unknown"] += 1
            else:
                # If "Number of Frames" tag is missing, consider it as single (likely single frame)
                results[folder_name]["single"] += 1
        except Exception:
            pass  # Not a DICOM file

# Print results
print(f"{'Folder':<30} {'Multi-slice':>12} {'Single-slice':>12} {'Unknown':>10}")
print("-" * 70)
for folder, counts in results.items():
    print(f"{folder:<30} {counts['multi']:>12} {counts['single']:>12} {counts['unknown']:>10}")
