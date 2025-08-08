# TOMO Center Slice Extractor

## Overview

This Python script processes DICOM images from digital breast tomosynthesis (TOMO) studies and extracts **the center slice** from the representative series for each target mammography view:

* **LCC** – Left Cranio-Caudal
* **RCC** – Right Cranio-Caudal
* **LMLO** – Left Medio-Lateral Oblique
* **RMLO** – Right Medio-Lateral Oblique

The script:

* Works with both **presentation** and **processing** modes.
* Ignores multi-frame DICOMs.
* Skips files larger than a given size limit (default: 100 MB).
* Handles irregular view name formats (e.g., `RLMO` → `RMLO`).
* Ensures safe file names and avoids overwriting.

---

## Features

* **Automatic view classification**
  Detects view type from DICOM tags `(0020,0060)`, `(0020,0062)`, `(0018,5101)` and, if needed, from `(0008,103E)` *Series Description*.

* **Representative series selection**
  For each view, the script selects the series with the **most slices**.

* **Center slice extraction**
  Picks the slice in the middle of the series based on:

  1. `InstanceNumber (0020,0013)`
  2. `ImagePositionPatient (0020,0032)` Z-coordinate
  3. Fallback: SOPInstanceUID string comparison

* **Safe output structure**
  Output subfolders have sanitized names (last 10 characters, special characters replaced).
  Filenames are prefixed with their view type (e.g., `LCC_filename.dcm`).

---

## Requirements

* Python 3.7+
* [pydicom](https://pydicom.github.io/)

Install dependencies:

```bash
pip install pydicom
```

---

## Usage

```bash
python tomo_center_slice.py /path/to/parent_folder [options]
```

### Positional arguments:

* **`parent_folder`**
  The parent folder containing subfolders with DICOM files.

### Options:

| Option                             | Description                                                             | Default                           |
| ---------------------------------- | ----------------------------------------------------------------------- | --------------------------------- |
| `--mb N`                           | Maximum file size in MB to include. Files larger than this are skipped. | 100                               |
| `--deep`                           | Recursively search all subfolders.                                      | Off                               |
| `--out NAME`                       | Name for output root folder.                                            | `_collected_center_slices_≤100MB` |
| `--mode {presentation,processing}` | Classification mode.                                                    | `presentation`                    |

---

## Example

```bash
python tomo_center_slice.py /data/TOMO --mb 50 --deep --out extracted_slices --mode presentation
```

**Output:**

```
! Parent folder: /data/TOMO
! Output root: /data/TOMO/extracted_slices
! Target views: LCC, RCC, LMLO, RMLO (RLMO notation normalized to RMLO)
! Size constraint: ≤ 50 MB
! Recursive exploration: ON
! Mode: Presentation

- Case001 → Case001 : LCC, RCC, LMLO, RMLO
- Case002 → Case002 : LCC, RMLO
...

! Done: Total copied files = 6
! Result location: /data/TOMO/extracted_slices
   (Subfolder names truncated to 10 characters, view prefixes added to filenames)
```

---

## Output Structure

```
output_root/
    <shortened_case_folder>/
        LCC_<filename>.dcm
        RCC_<filename>.dcm
        LMLO_<filename>.dcm
        RMLO_<filename>.dcm
```

---

## Notes

* Only **single-slice TOMO** images are included. Multi-frame DICOMs are excluded.
* File names are guaranteed to be safe for all OSes.
* If two files have the same name, a numeric suffix will be added.

---

## License

This project is licensed under the MIT License.
