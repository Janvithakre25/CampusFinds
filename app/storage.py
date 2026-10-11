import os
import uuid
from werkzeug.utils import secure_filename
from flask import current_app, url_for
import logging

logger = logging.getLogger(__name__)

def allowed_file(filename):
    """Check if file extension is an allowed image type."""
    if not filename or '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in current_app.config.get('ALLOWED_EXTENSIONS', {'png', 'jpg', 'jpeg', 'webp', 'gif'})

def save_uploaded_file(file_storage):
    """
    Saves an uploaded file either locally or to Amazon S3 depending on config.
    Returns relative path (or S3 URL) for storage in database, or None if invalid.
    """
    if not file_storage or file_storage.filename == '':
        return None

    if not allowed_file(file_storage.filename):
        raise ValueError("Invalid file extension. Only PNG, JPG, JPEG, WEBP, and GIF are allowed.")

    ext = file_storage.filename.rsplit('.', 1)[1].lower()
    unique_filename = f"{uuid.uuid4().hex}.{ext}"

    backend = current_app.config.get('STORAGE_BACKEND', 'local')

    if backend == 's3':
        return _save_to_s3(file_storage, unique_filename)
    else:
        return _save_to_local(file_storage, unique_filename)

def _save_to_local(file_storage, filename):
    """Saves file to local uploads directory."""
    upload_folder = current_app.config.get('UPLOAD_FOLDER', os.path.join('app', 'static', 'uploads'))
    os.makedirs(upload_folder, exist_ok=True)
    destination = os.path.join(upload_folder, filename)
    file_storage.save(destination)
    return filename

def _save_to_s3(file_storage, filename):
    """
    Uploads file to Amazon S3 bucket.
    Falls back gracefully to local storage if AWS credentials or bucket are not configured.
    """
    bucket_name = current_app.config.get('AWS_S3_BUCKET_NAME')
    if not bucket_name:
        logger.warning("AWS_S3_BUCKET_NAME not set. Falling back to local storage.")
        return _save_to_local(file_storage, filename)

    try:
        import boto3
        s3_kwargs = {
            'region_name': current_app.config.get('AWS_REGION', 'us-east-1')
        }
        # In AWS EC2 / ECS / Lambda, IAM Role credentials are loaded automatically.
        if current_app.config.get('AWS_ACCESS_KEY_ID') and current_app.config.get('AWS_SECRET_ACCESS_KEY'):
            s3_kwargs['aws_access_key_id'] = current_app.config.get('AWS_ACCESS_KEY_ID')
            s3_kwargs['aws_secret_access_key'] = current_app.config.get('AWS_SECRET_ACCESS_KEY')

        s3_client = boto3.client('s3', **s3_kwargs)
        s3_key = f"items/{filename}"

        s3_client.upload_fileobj(
            file_storage,
            bucket_name,
            s3_key,
            ExtraArgs={'ContentType': file_storage.content_type}
        )
        return f"s3://{bucket_name}/{s3_key}"
    except Exception as e:
        logger.error(f"S3 upload failed: {e}. Falling back to local storage.")
        file_storage.seek(0)
        return _save_to_local(file_storage, filename)

def get_image_url(image_reference):
    """
    Generates a web-accessible URL for an image reference.
    - If None, returns None.
    - If local filename, returns Flask static url.
    - If S3 URI, generates a presigned secure S3 URL if AWS configured, or public S3 link.
    """
    if not image_reference:
        return None

    if image_reference.startswith('s3://'):
        # Parse S3 URI
        parts = image_reference.replace('s3://', '').split('/', 1)
        bucket = parts[0]
        key = parts[1] if len(parts) > 1 else ''
        try:
            import boto3
            s3_client = boto3.client('s3', region_name=current_app.config.get('AWS_REGION', 'us-east-1'))
            # Generate temporary presigned URL (1 hour expiry) for private S3 storage
            return s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket, 'Key': key},
                ExpiresIn=3600
            )
        except Exception as e:
            logger.warning(f"Failed to generate presigned S3 URL: {e}")
            return f"https://{bucket}.s3.amazonaws.com/{key}"

    if image_reference.startswith('http://') or image_reference.startswith('https://'):
        return image_reference

    # Otherwise it's a local filename in uploads
    return url_for('static', filename=f"uploads/{image_reference}")
