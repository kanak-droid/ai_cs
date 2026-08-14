"""Local disk storage for astrologer-shared photos/videos (screenshots, profile
photos). Good enough for a single-instance dev/demo deployment; swapping to
real object storage (S3, GCS) later only means changing this module and the
upload route — nothing else references the filesystem path directly.
"""

from pathlib import Path

UPLOAD_DIR = Path(__file__).resolve().parents[2] / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
