#!/usr/bin/env python3
"""
Cloudflare R2 Manager
Handles R2 bucket operations, file uploads/downloads, and configuration
"""

import os
import sys
import boto3
import argparse
from pathlib import Path
from botocore.config import Config
from botocore.exceptions import ClientError
import mimetypes

class R2Manager:
    def __init__(self, account_id, access_key_id, secret_access_key, bucket_name):
        self.account_id = account_id
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key
        self.bucket_name = bucket_name

        # Configure R2 client with Cloudflare-specific settings
        config = Config(
            signature_version='s3v4',
            region_name='auto',
            s3={
                'addressing_style': 'virtual'
            }
        )

        self.client = boto3.client(
            's3',
            endpoint_url=f'https://{account_id}.r2.cloudflarestorage.com',
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            config=config
        )

    def create_bucket(self):
        """Create an R2 bucket"""
        try:
            self.client.create_bucket(Bucket=self.bucket_name)
            print(f"✅ Bucket '{self.bucket_name}' created successfully")
            return True
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'BucketAlreadyOwnedByYou':
                print(f"ℹ️  Bucket '{self.bucket_name}' already exists")
                return True
            else:
                print(f"❌ Error creating bucket: {e}")
                return False

    def upload_file(self, local_path, object_key=None):
        """Upload a file to R2"""
        if not Path(local_path).exists():
            print(f"❌ Local file does not exist: {local_path}")
            return False

        if object_key is None:
            object_key = Path(local_path).name

        try:
            # Determine content type
            content_type, _ = mimetypes.guess_type(local_path)
            if content_type is None:
                content_type = 'application/octet-stream'

            self.client.upload_file(
                local_path,
                self.bucket_name,
                object_key,
                ExtraArgs={'ContentType': content_type}
            )

            print(f"✅ Uploaded '{local_path}' to '{self.bucket_name}/{object_key}'")
            print(f"   URL: https://{self.bucket_name}.r2.wasabisys.com/{object_key}")
            return True
        except ClientError as e:
            print(f"❌ Error uploading file: {e}")
            return False

    def download_file(self, object_key, local_path):
        """Download a file from R2"""
        try:
            self.client.download_file(self.bucket_name, object_key, local_path)
            print(f"✅ Downloaded '{self.bucket_name}/{object_key}' to '{local_path}'")
            return True
        except ClientError as e:
            print(f"❌ Error downloading file: {e}")
            return False

    def list_objects(self, prefix=""):
        """List objects in the bucket"""
        try:
            response = self.client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )

            if 'Contents' in response:
                print(f"📁 Objects in bucket '{self.bucket_name}':")
                for obj in response['Contents']:
                    size = obj['Size']
                    modified = obj['LastModified'].strftime('%Y-%m-%d %H:%M:%S')
                    print(f"  {obj['Key']} ({size} bytes, {modified})")
            else:
                print(f"📁 No objects found in bucket '{self.bucket_name}'")

            return True
        except ClientError as e:
            print(f"❌ Error listing objects: {e}")
            return False

    def delete_object(self, object_key):
        """Delete an object from R2"""
        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=object_key)
            print(f"✅ Deleted '{self.bucket_name}/{object_key}'")
            return True
        except ClientError as e:
            print(f"❌ Error deleting object: {e}")
            return False

    def generate_presigned_url(self, object_key, expiration=3600):
        """Generate a presigned URL for temporary access"""
        try:
            url = self.client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': object_key},
                ExpiresIn=expiration
            )
            print(f"🔗 Presigned URL for '{object_key}': {url}")
            print(f"   Expires in: {expiration} seconds")
            return url
        except ClientError as e:
            print(f"❌ Error generating presigned URL: {e}")
            return None

    def set_cors_policy(self, origins=None):
        """Set CORS policy for the bucket"""
        if origins is None:
            origins = ['https://*', 'http://localhost:*']

        cors_config = {
            'CORSRules': [
                {
                    'AllowedHeaders': ['*'],
                    'AllowedMethods': ['GET', 'PUT', 'POST', 'DELETE', 'HEAD'],
                    'AllowedOrigins': origins,
                    'ExposeHeaders': ['ETag', 'Content-Length', 'Content-Type'],
                    'MaxAgeSeconds': 3000
                }
            ]
        }

        try:
            self.client.put_bucket_cors(
                Bucket=self.bucket_name,
                CORSConfiguration=cors_config
            )
            print(f"✅ CORS policy set for bucket '{self.bucket_name}'")
            print(f"   Origins: {origins}")
            return True
        except ClientError as e:
            print(f"❌ Error setting CORS policy: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(description='Cloudflare R2 Manager')
    parser.add_argument('--account-id', required=True, help='Cloudflare Account ID')
    parser.add_argument('--access-key-id', required=True, help='R2 Access Key ID')
    parser.add_argument('--secret-access-key', required=True, help='R2 Secret Access Key')
    parser.add_argument('--bucket', required=True, help='R2 Bucket Name')

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Create bucket command
    create_parser = subparsers.add_parser('create-bucket', help='Create an R2 bucket')

    # Upload command
    upload_parser = subparsers.add_parser('upload', help='Upload a file to R2')
    upload_parser.add_argument('local_path', help='Local file path to upload')
    upload_parser.add_argument('--key', help='Object key in R2 (defaults to filename)')

    # Download command
    download_parser = subparsers.add_parser('download', help='Download a file from R2')
    download_parser.add_argument('object_key', help='Object key in R2')
    download_parser.add_argument('local_path', help='Local destination path')

    # List command
    list_parser = subparsers.add_parser('list', help='List objects in bucket')
    list_parser.add_argument('--prefix', default='', help='Filter objects by prefix')

    # Delete command
    delete_parser = subparsers.add_parser('delete', help='Delete an object from R2')
    delete_parser.add_argument('object_key', help='Object key to delete')

    # Presigned URL command
    presigned_parser = subparsers.add_parser('presigned-url', help='Generate presigned URL')
    presigned_parser.add_argument('object_key', help='Object key to generate URL for')
    presigned_parser.add_argument('--expires', type=int, default=3600, help='Expiration time in seconds')

    # Set CORS command
    cors_parser = subparsers.add_parser('set-cors', help='Set CORS policy')
    cors_parser.add_argument('--origins', nargs='+', help='Allowed origins for CORS')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Initialize R2 manager
    r2 = R2Manager(
        account_id=args.account_id,
        access_key_id=args.access_key_id,
        secret_access_key=args.secret_access_key,
        bucket_name=args.bucket
    )

    # Execute command
    if args.command == 'create-bucket':
        r2.create_bucket()
    elif args.command == 'upload':
        r2.upload_file(args.local_path, args.key)
    elif args.command == 'download':
        r2.download_file(args.object_key, args.local_path)
    elif args.command == 'list':
        r2.list_objects(args.prefix)
    elif args.command == 'delete':
        r2.delete_object(args.object_key)
    elif args.command == 'presigned-url':
        r2.generate_presigned_url(args.object_key, args.expires)
    elif args.command == 'set-cors':
        origins = args.origins or ['https://*', 'http://localhost:*']
        r2.set_cors_policy(origins)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()