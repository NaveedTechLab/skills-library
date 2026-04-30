# Cloudflare R2 Configuration Guide

## R2 Bucket Setup

### Creating an R2 Bucket
```bash
# Using Wrangler CLI
wrangler r2 bucket create your-bucket-name --env production

# Using AWS CLI compatible endpoint
aws s3 mb s3://your-bucket-name \
  --endpoint-url=https://your-account-id.r2.cloudflarestorage.com
```

## R2 Access Keys Setup

### Creating R2 API Tokens
1. Log into Cloudflare Dashboard
2. Go to R2 Settings
3. Navigate to "Manage R2 API Tokens"
4. Create a new token with appropriate permissions

### Environment Variables
```
CLOUDFLARE_ACCOUNT_ID=your_account_id_here
CLOUDFLARE_R2_ACCESS_KEY_ID=your_access_key_id
CLOUDFLARE_R2_SECRET_ACCESS_KEY=your_secret_access_key
CLOUDFLARE_R2_BUCKET_NAME=your_bucket_name
CLOUDFLARE_R2_PUBLIC_DOMAIN=https://your_subdomain.r2.cloudflarestorage.com
```

## Python Boto3 Configuration

### R2 Client Setup
```python
import boto3
from botocore.config import Config

def create_r2_client(account_id, access_key_id, secret_access_key):
    """
    Create an S3-compatible client for Cloudflare R2
    """
    config = Config(
        signature_version='s3v4',
        region_name='auto',  # R2 uses 'auto' for global endpoint
        s3={
            'addressing_style': 'virtual'  # Use virtual-hosted style
        }
    )

    s3_client = boto3.client(
        's3',
        endpoint_url=f'https://{account_id}.r2.cloudflarestorage.com',
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
        config=config
    )

    return s3_client

def upload_file_to_r2(client, bucket_name, file_path, object_key):
    """
    Upload a file to R2 bucket
    """
    client.upload_file(file_path, bucket_name, object_key)

    # Generate public URL
    public_url = f'https://{bucket_name}.r2.wasabisys.com/{object_key}'
    return public_url

def upload_bytes_to_r2(client, bucket_name, data, object_key, content_type='application/octet-stream'):
    """
    Upload binary data directly to R2
    """
    client.put_object(
        Bucket=bucket_name,
        Key=object_key,
        Body=data,
        ContentType=content_type
    )

    # Generate public URL
    public_url = f'https://{bucket_name}.r2.wasabisys.com/{object_key}'
    return public_url
```

## CORS Configuration for Web Applications

### Setting CORS Policy
```python
def set_cors_policy(client, bucket_name):
    """
    Set CORS policy for web application access
    """
    cors_configuration = {
        'CORSRules': [
            {
                'AllowedHeaders': ['*'],
                'AllowedMethods': ['GET', 'PUT', 'POST', 'DELETE', 'HEAD'],
                'AllowedOrigins': [
                    'https://yourdomain.com',
                    'https://*.yourdomain.com',
                    'http://localhost:*'
                ],
                'ExposeHeaders': ['ETag', 'Content-Length', 'Content-Type'],
                'MaxAgeSeconds': 3000
            }
        ]
    }

    client.put_bucket_cors(
        Bucket=bucket_name,
        CORSConfiguration=cors_configuration
    )
```

## Presigned URLs for Secure Uploads

### Generating Presigned URLs
```python
def generate_presigned_post(client, bucket_name, object_name, expiration=3600):
    """
    Generate a presigned URL for secure uploads
    """
    return client.generate_presigned_post(
        Bucket=bucket_name,
        Key=object_name,
        ExpiresIn=expiration
    )

def generate_presigned_download_url(client, bucket_name, object_name, expiration=3600):
    """
    Generate a presigned URL for secure downloads
    """
    return client.generate_presigned_url(
        'get_object',
        Params={'Bucket': bucket_name, 'Key': object_name},
        ExpiresIn=expiration
    )
```

## R2 Bucket Lifecycle Rules

### Setting Up Lifecycle Policies
```bash
# Example lifecycle configuration
cat > lifecycle-config.json <<EOF
{
  "Rules": [
    {
      "ID": "Delete old objects",
      "Status": "Enabled",
      "Filter": {
        "Prefix": "temp/"
      },
      "Expiration": {
        "Days": 7
      }
    }
  ]
}
EOF

# Apply lifecycle configuration
aws s3api put-bucket-lifecycle-configuration \
  --bucket your-bucket-name \
  --lifecycle-configuration file://lifecycle-config.json \
  --endpoint-url=https://your-account-id.r2.cloudflarestorage.com
```

## R2 with Django Applications

### Django Storage Backend
```python
# settings.py
INSTALLED_APPS = [
    # ... other apps
    'storages',
]

# Media and static files
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
STATICFILES_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

AWS_ACCESS_KEY_ID = os.environ.get('CLOUDFLARE_R2_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.environ.get('CLOUDFLARE_R2_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = os.environ.get('CLOUDFLARE_R2_BUCKET_NAME')
AWS_S3_ENDPOINT_URL = f'https://{os.environ.get("CLOUDFLARE_ACCOUNT_ID")}.r2.cloudflarestorage.com'
AWS_S3_REGION_NAME = 'auto'  # Required for R2
AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.r2.wasabisys.com'
AWS_DEFAULT_ACL = 'public-read'
AWS_S3_OBJECT_PARAMETERS = {
    'CacheControl': 'max-age=86400',
}
```

## R2 with FastAPI Applications

### FastAPI Upload Endpoint
```python
from fastapi import FastAPI, UploadFile, File
from typing import Optional
import boto3
import uuid
from botocore.config import Config

app = FastAPI()

def get_r2_client():
    config = Config(
        signature_version='s3v4',
        region_name='auto',
        s3={
            'addressing_style': 'virtual'
        }
    )

    return boto3.client(
        's3',
        endpoint_url=f'https://{os.environ.get("CLOUDFLARE_ACCOUNT_ID")}.r2.cloudflarestorage.com',
        aws_access_key_id=os.environ.get('CLOUDFLARE_R2_ACCESS_KEY_ID'),
        aws_secret_access_key=os.environ.get('CLOUDFLARE_R2_SECRET_ACCESS_KEY'),
        config=config
    )

@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    r2_client = get_r2_client()
    bucket_name = os.environ.get('CLOUDFLARE_R2_BUCKET_NAME')

    # Generate unique filename
    file_extension = file.filename.split('.')[-1]
    unique_filename = f"{uuid.uuid4()}.{file_extension}"

    # Upload file
    file_content = await file.read()
    r2_client.put_object(
        Bucket=bucket_name,
        Key=unique_filename,
        Body=file_content,
        ContentType=file.content_type
    )

    public_url = f'https://{bucket_name}.r2.wasabisys.com/{unique_filename}'
    return {"filename": unique_filename, "url": public_url}
```