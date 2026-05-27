import uuid
from minio import Minio
from minio.error import S3Error
from fastapi import UploadFile
from io import BytesIO
from app.config import get_settings

settings = get_settings()

# Initialize MinIO client
minio_client = Minio(
    settings.MINIO_ENDPOINT,
    access_key=settings.MINIO_ACCESS_KEY,
    secret_key=settings.MINIO_SECRET_KEY,
    secure=settings.MINIO_USE_SSL,
)


def ensure_bucket_exists():
    """Create the bucket if it doesn't exist."""
    try:
        if not minio_client.bucket_exists(settings.MINIO_BUCKET_NAME):
            minio_client.make_bucket(settings.MINIO_BUCKET_NAME)
            # Set bucket policy for public read access
            import json
            policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"AWS": "*"},
                        "Action": ["s3:GetObject"],
                        "Resource": [f"arn:aws:s3:::{settings.MINIO_BUCKET_NAME}/*"],
                    }
                ],
            }
            minio_client.set_bucket_policy(settings.MINIO_BUCKET_NAME, json.dumps(policy))
    except S3Error as e:
        print(f"MinIO bucket error: {e}")


def upload_image(file: UploadFile) -> str:
    """Upload an image file to MinIO and return the URL."""
    ensure_bucket_exists()

    # Generate unique filename
    ext = file.filename.split(".")[-1] if file.filename else "jpg"
    unique_filename = f"{uuid.uuid4().hex}.{ext}"

    # Read file content
    file_content = file.file.read()
    file_size = len(file_content)
    file_stream = BytesIO(file_content)

    # Upload to MinIO
    minio_client.put_object(
        settings.MINIO_BUCKET_NAME,
        unique_filename,
        file_stream,
        file_size,
        content_type=file.content_type or "image/jpeg",
    )

    # Build URL
    protocol = "https" if settings.MINIO_USE_SSL else "http"
    url = f"{protocol}://{settings.MINIO_ENDPOINT}/{settings.MINIO_BUCKET_NAME}/{unique_filename}"
    return url


def delete_image(image_url: str) -> bool:
    """Delete an image from MinIO by its URL."""
    try:
        # Extract object name from URL
        object_name = image_url.split(f"/{settings.MINIO_BUCKET_NAME}/")[-1]
        minio_client.remove_object(settings.MINIO_BUCKET_NAME, object_name)
        return True
    except S3Error:
        return False
