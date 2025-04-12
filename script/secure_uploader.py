#!/usr/bin/env python3
import boto3
import os
import sys
from datetime import datetime, timedelta
from botocore.exceptions import ClientError, NoCredentialsError

# Configuration - Load from environment variables
BUCKET_NAME = os.getenv('S3_BUCKET_NAME')
KMS_KEY_ARN = os.getenv('AWS_KMS_KEY_ARN')
ALLOWED_USERS = [
    os.getenv('ADMIN_USER_ARN'),  # Set these in your environment
    os.getenv('EDITOR_USER_ARN')  # or replace with actual ARNs
]

def verify_uploader_identity():
    """Verify the AWS user matches our Terraform-created users"""
    sts = boto3.client('sts')
    try:
        identity = sts.get_caller_identity()

        if identity['Arn'] not in ALLOWED_USERS:
            print(f"❌ ERROR: Unauthorized user: {identity['Arn']}")
            print("Allowed users:")
            for user in ALLOWED_USERS:
                print(f" - {user}")
            sys.exit(1)

        print(f"✅ Verified identity: {identity['Arn']}")
        return identity

    except (ClientError, NoCredentialsError) as e:
        print(f"🚨 AWS Authentication Error: {str(e)}")
        sys.exit(1)
if __name__ == "__main__":
    # Check environment variables
    if not all([BUCKET_NAME, KMS_KEY_ARN, all(ALLOWED_USERS)]):
        print("Missing required environment variables:")
        print(" - S3_BUCKET_NAME")
        print(" - AWS_KMS_KEY_ARN")
        print(" - ADMIN_USER_ARN")
        print(" - EDITOR_USER_ARN")
        sys.exit(1)

    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <file_path> [expiry_hours]")
        sys.exit(1)

    file_path = sys.argv[1]
    expires_hours = int(sys.argv[2]) if len(sys.argv) > 2 else 1

    result = secure_upload(file_path, expires_hours)

    print("\n🔗 Presigned URL (expires at {}):".format(result['expires_at']))
    print(result['url'])
    print("\nℹ️ Object Key:", result['object_key'])

# def multipart_upload(file_path, bucket, key, credentials, chunk_size=DEFAULT_CHUNK_SIZE):
#     s3 = boto3.client(
#         's3',
#         aws_access_key_id=credentials['AccessKeyId'],
#         aws_secret_access_key=credentials['SecretAccessKey'],
#         aws_session_token=credentials['SessionToken']
#     )
    
#     file_size = os.path.getsize(file_path)
#     chunks_count = math.ceil(file_size / chunk_size)
    
#     # Initiate multipart upload
#     mpu = s3.create_multipart_upload(
#         Bucket=bucket,
#         Key=key,
#         ServerSideEncryption='aws:kms',
#         SSEKMSKeyId=credentials.get('kms_key_arn', None)
#     )
#     mpu_id = mpu['UploadId']
    
#     parts = []
#     try:
#         with open(file_path, 'rb') as f:
#             for i in range(1, chunks_count + 1):
#                 print(f"Uploading part {i}/{chunks_count}")
#                 offset = chunk_size * (i - 1)
#                 bytes_to_read = min(chunk_size, file_size - offset)
#                 f.seek(offset)
                
#                 part = s3.upload_part(
#                     Bucket=bucket,
#                     Key=key,
#                     PartNumber=i,
#                     UploadId=mpu_id,
#                     Body=f.read(bytes_to_read)
#                 parts.append({'PartNumber': i, 'ETag': part['ETag']})
                
#         # Complete the upload
#         result = s3.complete_multipart_upload(
#             Bucket=bucket,
#             Key=key,
#             UploadId=mpu_id,
#             MultipartUpload={'Parts': parts}
#         )
#         return result['Location']
        
#     except Exception as e:
#         print(f"Error during upload: {e}")
#         s3.abort_multipart_upload(
#             Bucket=bucket,
#             Key=key,
#             UploadId=mpu_id
#         )
#         raise

# def main():
#     parser = argparse.ArgumentParser()
#     parser.add_argument("file", help="File to upload")
#     parser.add_argument("--bucket", required=True)
#     parser.add_argument("--role-arn", required=True)
#     parser.add_argument("--expiry", type=int, default=72)
#     parser.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE)
#     args = parser.parse_args()

#     # Assume role with longer duration
#     sts = boto3.client('sts')
#     creds = sts.assume_role(
#         RoleArn=args.role_arn,
#         RoleSessionName='s3-multipart-upload',
#         DurationSeconds=3600 * 3  # 3 hour session for large files
#     )['Credentials']

#     # Upload file
#     key = os.path.basename(args.file)
#     try:
#         upload_location = multipart_upload(
#             args.file, 
#             args.bucket, 
#             key, 
#             creds, 
#             args.chunk_size
#         )
#         print(f"Successfully uploaded to {upload_location}")
        
#         # Generate pre-signed URL
#         s3 = boto3.client(
#             's3',
#             aws_access_key_id=creds['AccessKeyId'],
#             aws_secret_access_key=creds['SecretAccessKey'],
#             aws_session_token=creds['SessionToken']
#         )
        
#         url = s3.generate_presigned_url(
#             'get_object',
#             Params={'Bucket': args.bucket, 'Key': key},
#             ExpiresIn=args.expiry*3600
#         )
#         print(f"\nPre-signed URL (expires in {args.expiry} hours):")
#         print(url)
        
#     except Exception as e:
#         print(f"Upload failed: {str(e)}")
#         exit(1)

# if __name__ == "__main__":
#     main()