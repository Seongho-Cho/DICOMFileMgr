import os
import sys
import shutil
import argparse
import re
from collections import defaultdict
import pydicom

TARGET_VIEWS = ["LCC", "RCC", "LMLO", "RMLO"]  # View targets
ACCEPT_RLMO = {"RLMO"}  # Normalize RLMO notation to RMLO

def safe_tail_name(name: str, tail_len: int = 10) -> str:
    tail = name[-tail_len:] if len(name) > tail_len else name
    for ch in '<>:"/\\|?*':
        tail = tail.replace(ch, "_")
    tail = tail.strip()
    return tail or "_empty_"

def ensure_unique_dir(base_dir: str, name: str) -> str:
    cand = os.path.join(base_dir, name)
    if not os.path.exists(cand):
        return cand
    i = 1
    while True:
        alt = os.path.join(base_dir, f"{name}_{i}")
        if not os.path.exists(alt):
            return alt
        i += 1

def get_tag_str(ds, tag):
    if tag in ds:
        val = ds[tag].value
        if isinstance(val, bytes):
            try:
                val = val.decode(errors="ignore")
            except Exception:
                pass
        return str(val).strip()
    return None

def normalize_view(view):
    if not view:
        return None
    v = view.strip().upper()
    repl = {"M-L-O": "MLO", "M L O": "MLO", "C-C": "CC", "C C": "CC"}
    return repl.get(v, v)

def guess_from_series(desc):
    if not desc:
        return None
    s = desc.upper()
    if re.search(r"\bL\s*CC\b|LCC\b|LCCID\b", s):
        return "LCC"
    if re.search(r"\bR\s*CC\b|RCC\b|RCCID\b", s):
        return "RCC"
    if re.search(r"\bL\s*MLO\b|LMLO\b|LMLOID\b", s):
        return "LMLO"
    if re.search(r"\bR\s*MLO\b|RMLO\b|RLMO\b|RMLOID\b", s):
        return "RMLO"  # Normalize RLMO to RMLO
    return None

def classify_view(ds, mode="presentation"):
    """
    Laterality (0020,0060) or Image Laterality (0020,0062) + View Position (0018,5101)
    If insufficient, estimate from Series Description (0008,103E).
    Returns: LCC / RCC / LMLO / RMLO / None
    """
    laterality = get_tag_str(ds, (0x0020, 0x0060)) or get_tag_str(ds, (0x0020, 0x0062))
    if laterality:
        laterality = laterality.upper()
        if laterality not in ("L", "R"):
            laterality = None

    view = normalize_view(get_tag_str(ds, (0x0018, 0x5101)))

    if mode == "presentation":
        # For presentation mode, prioritize based on view position
        if laterality and view in ("CC", "MLO"):
            return f"{laterality}{view}"
    elif mode == "processing":
        # In processing mode, handle series differently, or just return view directly
        return view

    guess = guess_from_series(get_tag_str(ds, (0x0008, 0x103E)))
    return guess

def slice_order_key(ds):
    """
    Slice order key: Prefer InstanceNumber(0020,0013), if absent use ImagePositionPatient[2] (Z from 0020,0032).
    If both are missing, fall back to SOPInstanceUID string comparison.
    """
    # InstanceNumber
    inst = None
    try:
        inst_str = get_tag_str(ds, (0x0020, 0x0013))
        if inst_str is not None and inst_str != "":
            inst = int(inst_str)
    except Exception:
        inst = None

    if inst is not None:
        return ("A", inst)

    # ImagePositionPatient Z
    try:
        ipp = ds.get((0x0020, 0x0032), None)
        if ipp is not None:
            val = ipp.value
            if isinstance(val, (list, tuple)) and len(val) >= 3:
                return ("B", float(val[2]))
            # Handle "x\y\z" string format
            if isinstance(val, str):
                parts = re.split(r"[\\, ]+", val.strip())
                if len(parts) >= 3:
                    return ("B", float(parts[2]))
    except Exception:
        pass

    # Fallback: SOPInstanceUID
    return ("C", get_tag_str(ds, (0x0008, 0x0018)) or "")

def copy_unique(src, dest_dir, prefix=None):
    base = os.path.basename(src)
    stem, ext = os.path.splitext(base)
    candidate = f"{prefix}_{base}" if prefix else base
    dst = os.path.join(dest_dir, candidate)
    if not os.path.exists(dst):
        shutil.copy2(src, dst)
        return dst
    i = 1
    while True:
        alt_name = f"{prefix + '_' if prefix else ''}{stem}_{i}{ext}"
        alt = os.path.join(dest_dir, alt_name)
        if not os.path.exists(alt):
            shutil.copy2(src, alt)
            return alt
        i += 1

def pick_center_slice(paths):
    """
    From the list of DICOM paths in the same series, return the file path of the central slice.
    """
    items = []
    for p in paths:
        try:
            ds = pydicom.dcmread(p, stop_before_pixels=True, force=True)
        except Exception:
            continue
        items.append((slice_order_key(ds), p))
    if not items:
        return None
    items.sort(key=lambda x: x[0])
    mid = len(items) // 2  # Middle
    return items[mid][1]

def process_subfolder(subfolder_path, out_root, size_max, deep, exclude_dir, mode="presentation"):
    """
    Process series of TOMO (single-slice) images under 100MB,
    copy one center slice for each LCC/RCC/LMLO/RMLO representative series.
    """
    sub_name = os.path.basename(subfolder_path.rstrip(os.sep))
    tail_name = safe_tail_name(sub_name, 10)
    dest_dir = ensure_unique_dir(out_root, tail_name)
    os.makedirs(dest_dir, exist_ok=True)

    # View -> SeriesUID -> File paths
    buckets = defaultdict(lambda: defaultdict(list))

    # Explorer
    if deep:
        walker = os.walk(subfolder_path)
    else:
        files = [os.path.join(subfolder_path, f) for f in os.listdir(subfolder_path)]
        walker = [(subfolder_path, [], [os.path.basename(p) for p in files if os.path.isfile(p)])]

    for root, _, files in walker:
        if exclude_dir and os.path.abspath(root).startswith(os.path.abspath(exclude_dir)):
            continue
        for fname in files:
            fpath = os.path.join(root, fname)
            if not os.path.isfile(fpath):
                continue
            try:
                size = os.path.getsize(fpath)
            except OSError:
                continue
            if size > size_max:
                continue  # Exclude files over 100MB

            try:
                ds = pydicom.dcmread(fpath, stop_before_pixels=True, force=True)
            except Exception:
                continue

            # Classify view based on the mode (presentation or processing)
            cls = classify_view(ds, mode)
            if cls in ACCEPT_RLMO:
                cls = "RMLO"
            if cls not in TARGET_VIEWS:
                continue

            # Assume TOMO (single slices): Skip if it's a multi-frame (NumberOfFrames)
            nof = get_tag_str(ds, (0x0028, 0x0008))  # Number of Frames
            if nof:
                try:
                    if int(nof) > 1:
                        continue  # Skip multi-frames
                except Exception:
                    pass  # Treat as single if parsing fails

            series_uid = get_tag_str(ds, (0x0020, 0x000E))  # SeriesInstanceUID
            if not series_uid:
                continue

            buckets[cls][series_uid].append(fpath)

    copied = {}

    # For each view: Select series with most slices -> Copy center slice
    for view in TARGET_VIEWS:
        series_map = buckets.get(view, {})
        if not series_map:
            continue
        # Choose representative series (most slices)
        series_uid, paths = max(series_map.items(), key=lambda kv: len(kv[1]))
        center = pick_center_slice(paths)
        if center:
            dst = copy_unique(center, dest_dir, prefix=view)
            copied[view] = {"series": series_uid, "src": center, "dst": dst, "count_in_series": len(paths)}

    return tail_name, dest_dir, copied

def main():
    ap = argparse.ArgumentParser(
        description="Copy the center slice of each representative series of TOMO images under 100MB for each view (LCC, RCC, LMLO, RMLO)."
    )
    ap.add_argument("parent_folder", help="Parent folder path")
    ap.add_argument("--mb", type=int, default=100, help="Maximum size (MB). Default=100 (only files below this size)")
    ap.add_argument("--deep", action="store_true", help="Recursively explore all depths (default is 1-level subfolders)")
    ap.add_argument("--out", default="_collected_center_slices_≤100MB", help="Output root folder name (default=_collected_center_slices_≤100MB)")
    ap.add_argument("--mode", choices=["presentation", "processing"], default="presentation", help="Mode to process images (default='presentation')")
    args = ap.parse_args()

    parent = args.parent_folder
    if not os.path.isdir(parent):
        print(f"! Folder not found: {parent}")
        sys.exit(1)

    size_max = args.mb * 1024 * 1024
    out_root = os.path.join(parent, args.out)
    os.makedirs(out_root, exist_ok=True)

    subfolders = [
        os.path.join(parent, d) for d in os.listdir(parent)
        if os.path.isdir(os.path.join(parent, d)) and os.path.join(parent, d) != out_root
    ]

    print(f"! Parent folder: {parent}")
    print(f"! Output root: {out_root}")
    print(f"! Target views: {', '.join(TARGET_VIEWS)} (RLMO notation normalized to RMLO)")
    print(f"! Size constraint: ≤ {args.mb} MB")
    print(f"! Recursive exploration: {'ON' if args.deep else 'OFF'}")
    print(f"! Mode: {args.mode.capitalize()}\n")

    grand_total = 0
    for sf in sorted(subfolders):
        tail, dest, copied = process_subfolder(
            subfolder_path=sf,
            out_root=out_root,
            size_max=size_max,
            deep=args.deep,
            exclude_dir=out_root,
            mode=args.mode
        )
        views_str = ", ".join(sorted(copied.keys())) if copied else "None"
        print(f"- {os.path.basename(sf)} → {os.path.basename(dest)} : {views_str}")
        grand_total += len(copied)

    print(f"\n! Done: Total copied files = {grand_total}")
    print(f"! Result location: {out_root}")
    print("   (Subfolder names truncated to 10 characters, view prefixes added to filenames)")
    
if __name__ == "__main__":
    main()
