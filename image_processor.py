# =============================
# image_processor.py (FINAL FIXED)
# =============================

import os
import io
from PIL import Image, ImageOps
import numpy as np

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
BACKGROUND_PATH = os.path.join(PROJECT_ROOT, "template", "background.png")
PERSON_PATH = os.path.join(PROJECT_ROOT, "template", "person.png")

PHOTOS_ROOT = os.environ.get("PHOTOS_ROOT", os.path.join(PROJECT_ROOT, "photos"))
FM_DIR = os.path.join(PHOTOS_ROOT, "FM")
A5_DIR = os.path.join(PHOTOS_ROOT, "A5")
THUMB_DIR = os.path.join(PHOTOS_ROOT, "Thumb")
PERS_DIR = os.path.join(PHOTOS_ROOT, "Perspective")
WEB300_DIR = os.path.join(PHOTOS_ROOT, "300")

for d in [FM_DIR, A5_DIR, THUMB_DIR, PERS_DIR, WEB300_DIR]:
    os.makedirs(d, exist_ok=True)

def trim_transparent(img, threshold=5):
    """
    Remove extra transparent area around PNG (CRITICAL for person image)
    """
    if img.mode != "RGBA":
        img = img.convert("RGBA")

    arr = np.array(img)
    alpha = arr[:, :, 3]

    mask = alpha > threshold
    if not np.any(mask):
        return img

    coords = np.argwhere(mask)
    y0, x0 = coords.min(axis=0)
    y1, x1 = coords.max(axis=0) + 1

    return img.crop((x0, y0, x1, y1))


# ------------------------------------------------
# Trim white bands (PIL port of `magick -fuzz 5% -trim +repage`)
# Used to strip white/near-white borders from FM source before
# generating the FM/A5/Thumb/Web300 derivatives.
# ------------------------------------------------
def trim_white_bands(img, fuzz=0.05):
    rgb = img.convert("RGB") if img.mode != "RGB" else img
    arr = np.array(rgb)
    tol = int(round(255 * fuzz))
    threshold = 255 - tol
    mask = ~((arr[:, :, 0] >= threshold) &
             (arr[:, :, 1] >= threshold) &
             (arr[:, :, 2] >= threshold))
    if not mask.any():
        return img
    rows = np.where(mask.any(axis=1))[0]
    cols = np.where(mask.any(axis=0))[0]
    y0, y1 = int(rows[0]), int(rows[-1]) + 1
    x0, x1 = int(cols[0]), int(cols[-1]) + 1
    if x0 == 0 and y0 == 0 and x1 == arr.shape[1] and y1 == arr.shape[0]:
        return img
    return img.crop((x0, y0, x1, y1))


def trim_file_inplace(path, fuzz=0.05, quality=95, dpi=(300, 300)):
    """Open `path`, trim white bands, save back as JPEG."""
    with Image.open(path) as im:
        im.load()
        trimmed = trim_white_bands(im, fuzz=fuzz)
        trimmed.convert("RGB").save(path, "JPEG", quality=quality, dpi=dpi)
    return path


# ------------------------------------------------
# TIFF → JPG
# ------------------------------------------------
def convert_tiff_to_jpg(input_path):
    base, _ = os.path.splitext(input_path)
    output_path = base + "_300dpi.jpg"

    with Image.open(input_path) as img:
        img = img.convert("RGB")
        img.save(output_path, "JPEG", dpi=(300, 300), quality=95)

    return output_path


# ------------------------------------------------
# A5 image
# ------------------------------------------------
A5_MAX = 2480

def create_a5(input_path, output_path, phys_w_cm=None, phys_h_cm=None):
    img = Image.open(input_path).convert("RGB")
    img = trim_white_bands(img)

    if phys_w_cm and phys_h_cm and phys_w_cm > 0 and phys_h_cm > 0:
        ratio = phys_w_cm / phys_h_cm
    else:
        ratio = img.width / img.height

    if ratio >= 1:
        tw, th = A5_MAX, max(1, round(A5_MAX / ratio))
    else:
        th, tw = A5_MAX, max(1, round(A5_MAX * ratio))

    a5 = img.resize((tw, th), Image.LANCZOS)
    a5.save(output_path, "JPEG", quality=95, dpi=(300, 300))
    return output_path


# ------------------------------------------------
# Thumbnail
# ------------------------------------------------
def create_thumbnail(input_path, output_path):
    img = Image.open(input_path).convert("RGB")
    img = trim_white_bands(img)
    img.thumbnail((250, 250), Image.LANCZOS)

    quality = 60
    for _ in range(10):
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=quality)
        if len(buf.getvalue()) / 1024 <= 10:
            with open(output_path, "wb") as f:
                f.write(buf.getvalue())
            return output_path
        quality -= 5

    return output_path


# ------------------------------------------------
# Remove white bg
# ------------------------------------------------
def remove_white(img):
    img = img.convert("RGBA")
    arr = np.array(img)
    r, g, b, a = np.rollaxis(arr, axis=-1)
    mask = (r > 240) & (g > 240) & (b > 240)
    arr[mask, 3] = 0
    return Image.fromarray(arr, "RGBA")


# ------------------------------------------------
# PERSPECTIVE — pixel-perfect collision, eye-level
# ------------------------------------------------

def _compute_person_eye_level(person_y, person_h, eye_level_ratio=0.14):
    return person_y + int(person_h * eye_level_ratio)

def _place_artwork_near_eye_level(art_h, wall_top, wall_bottom, eye_level_y):
    centered_y = int(eye_level_y - (art_h / 2))
    min_y, max_y = wall_top, wall_bottom - art_h
    if max_y < min_y:
        return wall_top
    return max(min_y, min(centered_y, max_y))

def _resolve_horizontal_art_position(preferred_ax, art_w, wall_left, wall_right,
                                      person_w, canvas_w, person_margin_right, min_visual_gap):
    person_left = canvas_w - person_w - person_margin_right
    max_ax = min(wall_right - art_w, person_left - min_visual_gap - art_w)
    min_ax = wall_left
    if max_ax < min_ax:
        return min_ax
    return max(min_ax, min(preferred_ax, max_ax))

def _build_art_position_candidates(preferred_ax, aw, wall_left, wall_right,
                                    person_w, canvas_w, person_margin_right, min_visual_gap):
    safe_ax = _resolve_horizontal_art_position(
        preferred_ax, aw, wall_left, wall_right,
        person_w, canvas_w, person_margin_right, min_visual_gap)
    person_left = canvas_w - person_w - person_margin_right
    hard_max_ax = min(wall_right - aw, person_left - aw)
    candidates = [preferred_ax, safe_ax, safe_ax - 40, safe_ax - 80, safe_ax - 120, hard_max_ax]
    normalized, seen = [], set()
    for ax in candidates:
        ax = int(max(wall_left, min(ax, wall_right - aw)))
        if ax not in seen:
            seen.add(ax)
            normalized.append(ax)
    return normalized

def _check_pixel_collision(art_img, art_x, art_y, person_img, person_x, person_y, gap=0):
    art_left, art_right   = art_x, art_x + art_img.width
    art_top, art_bottom   = art_y, art_y + art_img.height
    person_left, person_right = person_x, person_x + person_img.width
    person_top, person_bottom = person_y, person_y + person_img.height
    if (art_right + gap < person_left or person_right + gap < art_left or
            art_bottom + gap < person_top or person_bottom + gap < art_top):
        return False
    art_pixels    = art_img.load()
    person_pixels = person_img.load()
    overlap_left   = max(art_left - gap,   person_left - gap)
    overlap_right  = min(art_right + gap,  person_right + gap)
    overlap_top    = max(art_top - gap,    person_top - gap)
    overlap_bottom = min(art_bottom + gap, person_bottom + gap)
    for y in range(int(overlap_top), int(overlap_bottom)):
        for x in range(int(overlap_left), int(overlap_right)):
            art_has = (art_left <= x < art_right and art_top <= y < art_bottom and
                       art_pixels[x - art_left, y - art_top][3] > 10)
            px_local_x = x - person_left
            px_local_y = y - person_top
            person_has = (person_left - gap <= x < person_right + gap and
                          person_top - gap <= y < person_bottom + gap and
                          0 <= px_local_x < person_img.width and
                          0 <= px_local_y < person_img.height and
                          person_pixels[px_local_x, px_local_y][3] > 10)
            if art_has and person_has:
                return True
    return False


def generate_perspective(
    artwork_path,
    output_path,
    artwork_width_cm=None,
    artwork_height_cm=None,
    canvas_w=2400,
    canvas_h=2800,
    person_real_cm=180,
    person_target_height=2000,
    person_min_scale=0.78,
    person_margin_right=50,
    person_margin_bottom=60,
    wall_left=120,
    wall_right_margin=500,
    wall_top=120,
    wall_bottom_ratio=0.72,
    art_aspect_ratio_min=0.2,
    art_aspect_ratio_max=5.0,
    eye_level_ratio=0.14,
    min_gap_px=20,
    output_dpi=300,
    output_quality=92,
):
    """
    Pixel-perfect perspective: artwork + 180 cm person silhouette.
    Eye-level placement + collision detection — no black banner.
    """
    from PIL import Image

    if artwork_width_cm is None or artwork_height_cm is None:
        return None
    if artwork_width_cm <= 0 or artwork_height_cm <= 0:
        return None
    if artwork_height_cm > 190:
        print(f"[PERS SKIP] Oversized height {artwork_height_cm}cm > 190cm")
        return None

    ratio = artwork_width_cm / artwork_height_cm
    if ratio > art_aspect_ratio_max or ratio < art_aspect_ratio_min:
        print(f"[PERS SKIP] Invalid ratio {ratio:.2f}")
        return None

    art_src = Image.open(artwork_path).convert("RGBA")
    art_src = remove_white(art_src)

    if art_src.width < 500 or art_src.height < 500:
        print(f"[PERS SKIP] Low resolution {art_src.width}x{art_src.height}")
        return None

    bg = Image.open(BACKGROUND_PATH).convert("RGBA")
    bg = bg.resize((canvas_w, canvas_h), Image.LANCZOS)

    person_src = Image.open(PERSON_PATH).convert("RGBA")
    person_src = remove_white(person_src)
    person_src = trim_transparent(person_src)

    person_original = person_src.resize(
        (int(person_src.width * person_target_height / person_src.height), person_target_height),
        Image.LANCZOS)

    px_per_cm_max = person_target_height / person_real_cm
    art_w_max = int(artwork_width_cm  * px_per_cm_max)
    art_h_max = int(artwork_height_cm * px_per_cm_max)
    if art_w_max <= 0 or art_h_max <= 0 or art_w_max > canvas_w or art_h_max > canvas_h:
        print(f"[PERS SKIP] Artwork exceeds canvas at max scale")
        return None

    wall_right  = canvas_w - wall_right_margin
    wall_bottom = int(canvas_h * wall_bottom_ratio)
    wall_w      = wall_right - wall_left

    art_ratio = artwork_width_cm / artwork_height_cm
    if art_ratio >= 1.2:
        min_visual_gap = 170
    elif art_ratio >= 0.95:
        min_visual_gap = 140
    else:
        min_visual_gap = 110

    person_scale_tests = [s for s in [1.0, 0.96, 0.92, 0.88, 0.84, 0.80, person_min_scale]
                          if s >= person_min_scale]

    best_layout, best_score = None, None

    for scale_test in person_scale_tests:
        p_h = int(person_target_height * scale_test)
        p_w = int(person_original.width * scale_test)
        test_person = person_original if scale_test == 1.0 else \
                      person_original.resize((p_w, p_h), Image.LANCZOS)

        px_per_cm = test_person.height / person_real_cm
        art_w = int(artwork_width_cm  * px_per_cm)
        art_h = int(artwork_height_cm * px_per_cm)
        if art_w <= 0 or art_h <= 0:
            continue

        art_resized  = art_src.resize((art_w, art_h), Image.LANCZOS)
        preferred_ax = wall_left + (wall_w - art_w) // 2
        test_px      = canvas_w - test_person.width - person_margin_right
        test_py      = canvas_h - test_person.height - person_margin_bottom
        eye_level_y  = _compute_person_eye_level(test_py, test_person.height, eye_level_ratio)
        test_ay      = _place_artwork_near_eye_level(art_h, wall_top, wall_bottom, eye_level_y)

        position_candidates = _build_art_position_candidates(
            preferred_ax, art_w, wall_left, wall_right,
            test_person.width, canvas_w, person_margin_right, min_visual_gap)

        for test_ax in position_candidates:
            right_gap    = test_px - (test_ax + art_w)
            collision_ok = not _check_pixel_collision(
                art_resized, test_ax, test_ay,
                test_person, test_px, test_py, gap=min_gap_px)
            score = (
                (100000 if not collision_ok else 0)
                + max(0, -right_gap) * 50
                + max(0, min_visual_gap - right_gap) * 8
                + abs(test_ax - preferred_ax)
                + (1.0 - scale_test) * 220
            )
            if best_layout is None or score < best_score:
                best_layout = (art_resized, test_person, test_px, test_py,
                               test_ax, test_ay, scale_test, right_gap, collision_ok)
                best_score  = score

    if best_layout is None:
        print("[PERS SKIP] No valid layout found")
        return None

    art, person, px, py, ax, ay, person_scale_used, right_gap, collision_ok = best_layout
    ax = max(wall_left, min(ax, wall_right  - art.width))
    ay = max(wall_top,  min(ay, wall_bottom - art.height))

    bg.alpha_composite(art,    (ax, ay))
    bg.alpha_composite(person, (px, py))
    bg.convert("RGB").save(output_path, "JPEG", dpi=(output_dpi, output_dpi), quality=output_quality)

    print(
        f"[PERS OK] {artwork_width_cm}x{artwork_height_cm}cm → {art.width}x{art.height}px "
        f"person_scale={person_scale_used:.2f} gap={right_gap}px "
        f"{'CLEAR' if collision_ok else 'TIGHT'}"
    )
    return output_path


# ------------------------------------------------
# Web 300
# ------------------------------------------------
#def create_web300(input_path, output_path):
 #   img = Image.open(input_path).convert("RGB")
  #  img = ImageOps.fit(img, (2480, 3508), Image.LANCZOS)
   # img.save(output_path, "JPEG", dpi=(300, 300), quality=90)
    #return output_path
def create_web300(input_path, output_path):
    img = Image.open(input_path).convert("RGB")
    img = trim_white_bands(img)
    img.save(output_path, "JPEG", dpi=(300, 300), quality=90)
    return output_path

# ------------------------------------------------
# MAIN PROCESSOR
# ------------------------------------------------
def process_uploaded_image(path,artwork_id,classification,should_generate_perspective=False,artwork_width_cm=None,artwork_height_cm=None):

    base = os.path.basename(path).split(".")[0]
    orig_ext = os.path.splitext(path)[1].lower()

    # STEP 1 — Convert TIFF to JPG properly
    if orig_ext in (".tif", ".tiff"):
        jpg_path = convert_tiff_to_jpg(path)
    else:
        jpg_path = path

    # STEP 2 — Save ORIGINAL (FM version)
    if orig_ext in (".tif", ".tiff"):
        fm_filename = f"{base}_300dpi.jpg"
    else:
        fm_filename = f"{base}.jpg"

    fm_out = os.path.join(FM_DIR, fm_filename)

    fm_img = Image.open(jpg_path).convert("RGB")
    fm_img = trim_white_bands(fm_img)
    fm_img.save(fm_out, "JPEG", dpi=(300, 300), quality=95)

    # STEP 3 — A5 image (driven by trimmed FM, physical ratio if provided)
    a5_out = os.path.join(A5_DIR, f"{base}_A5.jpg")
    create_a5(fm_out, a5_out, artwork_width_cm, artwork_height_cm)

    # STEP 4 — Thumbnail (use trimmed FM)
    thumb_out = os.path.join(THUMB_DIR, f"{base}_thumb.jpg")
    create_thumbnail(fm_out, thumb_out)

    web300_out = None
    if classification == "MAIN":
        web300_out = os.path.join(WEB300_DIR, f"{base}_WEB300.jpg")
        create_web300(fm_out, web300_out)
    # STEP 5 — Perspective (skip sculpture)
    pers_out = None
    # if classification != "Sculpture":
    #     pers_out = os.path.join(PERS_DIR, f"{base}_PERS.jpg")
    #     generate_perspective(jpg_path, pers_out)
    
    # if should_generate_perspective:
    #     # uses SAME background.png (existing workflow)
    #     pers_out = os.path.join(PERS_DIR, f"{base}_PERS.jpg")
    #     generate_perspective(jpg_path, pers_out)

    if should_generate_perspective and artwork_width_cm and artwork_height_cm:
        pers_out = os.path.join(PERS_DIR, f"{base}_PERS.jpg")
        pers_out = generate_perspective(
            fm_out,
            pers_out,
            artwork_width_cm,
            artwork_height_cm
        )
    else:
        pers_out = None

    return {
        "original": fm_out,
        "a5": a5_out,
        "thumb": thumb_out,
        "perspective": pers_out,
        "web300": web300_out
    }
