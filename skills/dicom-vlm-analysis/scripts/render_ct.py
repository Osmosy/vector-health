#!/usr/bin/env python3
"""Render CT DICOM series to PNG with brain + bone windows.

Usage:
  python render_ct.py --root <DICOM_dir> [--out /tmp/ct_png] [--series 5]
  python render_ct.py --root <dir> --brain 80 40 --bone 2000 350
"""
import os
import argparse
import pydicom
from pydicom import dcmread
import numpy as np
from PIL import Image


def load_series(root):
    series = {}
    for f in sorted(os.listdir(root)):
        if not f.lower().endswith('.dcm'):
            continue
        try:
            ds = dcmread(os.path.join(root, f), force=True)
        except Exception:
            continue
        if getattr(ds, 'Modality', '') != 'CT':
            continue
        # Toshiba writes some series without SeriesInstanceUID/SeriesNumber:
        # fall back to filename prefix (IMG-0005-*).
        sn = str(getattr(ds, 'SeriesNumber', None) or 'uid_' + f.split('-')[0])
        z = None
        try:
            z = float(ds.ImagePositionPatient[2])
        except Exception:
            z = None
        series.setdefault(sn, []).append((z, ds))
    for sn in series:
        series[sn].sort(key=lambda x: (x[0] is None, x[0] or 0))
    return series


def hu(ds):
    a = ds.pixel_array.astype(np.float32)
    if hasattr(ds, 'RescaleSlope'):
        a = a * float(ds.RescaleSlope) + float(ds.RescaleIntercept)
    return a


def window(a, w, l):
    lo, hi = l - w / 2.0, l + w / 2.0
    return (np.clip((a - lo) / (hi - lo), 0, 1) * 255).astype(np.uint8)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', required=True, help='directory containing .dcm files')
    ap.add_argument('--out', default='/tmp/ct_png')
    ap.add_argument('--series', help='render only this series number')
    ap.add_argument('--brain', nargs=2, type=float, default=[80, 40],
                    metavar=('W', 'L'), help='brain window (default 80 40)')
    ap.add_argument('--bone', nargs=2, type=float, default=[2000, 350],
                    metavar=('W', 'L'), help='bone window (default 2000 350)')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    for sn, items in load_series(a.root).items():
        if a.series and sn != a.series:
            continue
        desc = getattr(items[0][1], 'SeriesDescription', '')
        print(f"Series {sn} '{desc}': {len(items)} slices")
        for i, (z, ds) in enumerate(items):
            img = hu(ds)
            Image.fromarray(window(img, *a.brain)).save(f"{a.out}/s{sn}_brain_{i:02d}.png")
            Image.fromarray(window(img, *a.bone)).save(f"{a.out}/s{sn}_bone_{i:02d}.png")
    print("Done ->", a.out)


if __name__ == '__main__':
    main()
