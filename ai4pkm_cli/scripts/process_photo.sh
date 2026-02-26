#!/bin/bash
# Photo Processing Script for PPP Workflow
# Extracts EXIF metadata and converts images to optimized JPEG format
# Skips work if outputs already exist
# Writes a full Markdown metadata report

set -euo pipefail

# Configuration
TARGET_SIZE_KB=100
OUTPUT_QUALITY=85
MIN_QUALITY=70
DEFAULT_WIDTH=1024
COLOR_PROFILE_PATH="/System/Library/ColorSync/Profiles/sRGB Profile.icc"

# Input validation
if [[ $# -ne 2 ]]; then
    echo "Usage: $0 <image_file> <output_dir>"
    exit 1
fi

input_file="$1"
DEST_DIR="$2"

input_basename=$(basename "$input_file")
input_name="${input_basename%.*}"
input_dir=$(dirname "$input_file")
input_ext="${input_basename##*.}"
input_ext_upper="$(printf '%s' "$input_ext" | tr '[:lower:]' '[:upper:]')"

if [[ ! -f "$input_file" ]]; then
    echo "Error: Input file not found: $input_file" >&2
    exit 1
fi

if ! command -v exiftool &> /dev/null; then
    echo "Error: exiftool is not installed. Install with: brew install exiftool" >&2
    exit 1
fi

if ! command -v sips &> /dev/null; then
    echo "Error: sips is not available" >&2
    exit 1
fi

mkdir -p "$DEST_DIR"

# --- Quick pre-check: Skip if ANY processed version exists ---
# This avoids expensive exiftool call when files are already processed
quick_check=$(find "$DEST_DIR" -name "*${input_name}.*" -print -quit 2>/dev/null)
if [[ -n "$quick_check" ]]; then
    echo "Skipping: File already exists - $quick_check"
    exit 0
fi

# --- Extract EXIF ---
datetime_original=$(exiftool -DateTimeOriginal -d "%Y-%m-%d %H:%M:%S" -s3 "$input_file" 2>/dev/null || echo "")
date_created=$(exiftool -CreateDate -d "%Y-%m-%d %H:%M:%S" -s3 "$input_file" 2>/dev/null || echo "")
gps_lat=$(exiftool -GPSLatitude -s3 "$input_file" 2>/dev/null || echo "")
gps_lon=$(exiftool -GPSLongitude -s3 "$input_file" 2>/dev/null || echo "")
camera_make=$(exiftool -Make -s3 "$input_file" 2>/dev/null || echo "")
camera_model=$(exiftool -Model -s3 "$input_file" 2>/dev/null || echo "")
lens_model=$(exiftool -LensModel -s3 "$input_file" 2>/dev/null || echo "")
focal_length=$(exiftool -FocalLength -s3 "$input_file" 2>/dev/null || echo "")
iso=$(exiftool -ISO -s3 "$input_file" 2>/dev/null || echo "")
aperture=$(exiftool -FNumber -s3 "$input_file" 2>/dev/null || echo "")
shutter_speed=$(exiftool -ShutterSpeed -s3 "$input_file" 2>/dev/null || echo "")
image_size=$(exiftool -ImageSize -s3 "$input_file" 2>/dev/null || echo "")
file_size=$(exiftool -FileSize -s3 "$input_file" 2>/dev/null || echo "")

photo_datetime="$datetime_original"
if [[ -z "$photo_datetime" ]]; then
    photo_datetime="$date_created"
fi

if [[ -z "$photo_datetime" ]]; then
    photo_date="unknown"
    photo_time="unknown"
    photo_date_formatted="unknown"
else
    photo_date="${photo_datetime%% *}"
    photo_time="${photo_datetime##* }"
    photo_date_formatted="${photo_date}"  # Keep YYYY-MM-DD format
fi

# Skip check already done above - proceeding with processing

# Use YYYY-MM-DD format with space separator to match repo convention
final_yaml="${DEST_DIR}/${photo_date_formatted} ${input_name}.yaml"
final_jpg="${DEST_DIR}/${photo_date_formatted} ${input_name}.jpg"

# --- Metadata file (full YAML) ---
cat > "$final_yaml" << EOF
original_file: "$input_basename"
photo_date: "$photo_date"
photo_time: "$photo_time"
created: $(date -Iseconds)
processed_on: $(date -Iseconds)

# Date & Time Information
datetime:
  original: "$photo_datetime"
  date: "$photo_date"
  time: "$photo_time"
  formatted: "${photo_date_formatted:-unknown}"

# Location Information
location:
EOF

if [[ -n "$gps_lat" && -n "$gps_lon" ]]; then
    cat >> "$final_yaml" << EOF
  gps_coordinates: "$gps_lat, $gps_lon"
  map_link: "https://maps.apple.com/?q=$gps_lat,$gps_lon"
  available: true
EOF
else
    cat >> "$final_yaml" << EOF
  gps_coordinates: null
  map_link: null
  available: false
EOF
fi

cat >> "$final_yaml" << EOF

# Camera Information
camera:
  make: "${camera_make:-N/A}"
  model: "${camera_model:-N/A}"
  lens: "${lens_model:-N/A}"

# Camera Settings
settings:
  focal_length: "${focal_length:-N/A}"
  iso: "${iso:-N/A}"
  aperture: "${aperture:-N/A}"
  shutter_speed: "${shutter_speed:-N/A}"

# File Information
file_info:
  original_size: "$image_size"
  file_size: "$file_size"
  target_size_kb: ${TARGET_SIZE_KB}
  conversion_quality: "${OUTPUT_QUALITY}%"

# Processing Information
processing:
  target_output_size: "<${TARGET_SIZE_KB}KB"
  conversion_quality: "${OUTPUT_QUALITY}%"
  processed_on: "$(date)"

# Content Management
content:
  suggested_caption: "[Add descriptive caption here based on image content]"
  
# Photolog Integration
photolog:
  time: "$photo_time"
  caption: "[Add caption]"
  file: "${photo_date_formatted:-YYYY-MM-DD} ${input_name}.jpg"
EOF

# --- Convert image ---
original_width=$(sips -g pixelWidth "$input_file" | awk '/pixelWidth:/ {print $2}')
original_height=$(sips -g pixelHeight "$input_file" | awk '/pixelHeight:/ {print $2}')

# Keep target_width = 1024 and set target_height same aspect ratio as original
target_width=$DEFAULT_WIDTH
target_height=$(( original_height * $DEFAULT_WIDTH / original_width ))

if [[ -f "$COLOR_PROFILE_PATH" ]]; then
  sips --matchTo "$COLOR_PROFILE_PATH" \
        -s format jpeg \
        -s formatOptions $OUTPUT_QUALITY \
        -Z $target_width \
        "$input_file" \
        --out "$final_jpg" >/dev/null
else
  sips -s format jpeg \
        -s formatOptions $OUTPUT_QUALITY \
        -Z $target_width \
        "$input_file" \
        --out "$final_jpg" >/dev/null
fi

exit 0
