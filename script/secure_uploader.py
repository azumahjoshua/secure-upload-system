#!/usr/bin/env python3
import boto3
import os
import sys
import math
from botocore.exceptions import ClientError
from botocore.config import Config
from datetime import datetime, timedelta

def debug_print_credentials(session):
    """Show current AWS credentials being used"""
    credentials = session.get_credentials()

    print("\n=== AWS Credentials Debug ===")
    print(f"Using profile: {session.profile_name or 'default'}")
    if credentials:
        masked_key = credentials.access_key[:4] + '...' + credentials.access_key[-4:]
        print(f"Access key: {masked_key}")
        print(f"Region: {session.region_name}")
        print("Transfer Acceleration: Enabled")
    else:
        print("No credentials found!")
    print("===========================\n")

def validate_config():
    """Validate all required environment variables"""
    required_vars = {
        'S3_BUCKET_NAME': os.getenv('S3_BUCKET_NAME'),
        'AWS_KMS_KEY_ARN': os.getenv('AWS_KMS_KEY_ARN'),
        'ACCESS_KEY': os.getenv('ACCESS_KEY'),
        'SECRET_KEY': os.getenv('SECRET_KEY'),
        'USER_ROLE': os.getenv('USER_ROLE', 'admin').lower(),
        'URL_EXPIRY_HOURS': os.getenv('URL_EXPIRY_HOURS', '24')
    }

    missing = [k for k, v in required_vars.items() if not v and k != 'URL_EXPIRY_HOURS']
    if missing:
        print(f"Error: Missing environment variables: {', '.join(missing)}")
        sys.exit(1)

    if required_vars['USER_ROLE'] not in ['admin', 'editor']:
        print("Error: Invalid USER_ROLE. Must be 'admin' or 'editor'")
        sys.exit(1)

    try:
        url_expiry = int(required_vars['URL_EXPIRY_HOURS'])
    except ValueError:
        print("Error: URL_EXPIRY_HOURS must be a valid integer")
        sys.exit(1)

    return {
        'bucket': required_vars['S3_BUCKET_NAME'],
        'kms_key': required_vars['AWS_KMS_KEY_ARN'],
        'access_key': required_vars['ACCESS_KEY'],
        'secret_key': required_vars['SECRET_KEY'],
        'user_role': required_vars['USER_ROLE'],
        'url_expiry_hours': url_expiry
    }

def create_s3_client(config):
    """Create authenticated S3 client with transfer acceleration and SigV4"""
    try:
        s3_config = Config(
            s3={'use_accelerate_endpoint': True},
            signature_version='s3v4'
        )

        session = boto3.Session(
            aws_access_key_id=config['access_key'],
            aws_secret_access_key=config['secret_key'],
            region_name=os.getenv('AWS_REGION', 'us-east-1')
        )

        sts = session.client('sts')
        identity = sts.get_caller_identity()
        print(f"Authenticated as {identity['Arn']} ({config['user_role']})")

        debug_print_credentials(session)
        return session.client('s3', config=s3_config)
    except ClientError as e:
        print(f"Authentication failed: {e.response['Error']['Message']}")
        sys.exit(1)

def generate_presigned_url(s3_client, bucket_name, object_key, expiry_hours):
    """Generate a presigned URL for the uploaded object"""
    try:
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket_name, 'Key': object_key},
            ExpiresIn=expiry_hours * 3600
        )
        expiry_time = (datetime.now() + timedelta(hours=expiry_hours)).strftime('%Y-%m-%d %H:%M:%S')
        print(f"\nPresigned URL (expires at {expiry_time}):")
        print(url)
        return url
    except ClientError as e:
        print(f"Failed to generate presigned URL: {e.response['Error']['Message']}")
        return None

def multipart_upload(s3_client, file_path, bucket_name, kms_key_arn, url_expiry_hours):
    """Handle multipart upload with KMS encryption and return presigned URL"""
    file_name = os.path.basename(file_path)

    try:
        response = s3_client.create_multipart_upload(
            Bucket=bucket_name,
            Key=file_name,
            ServerSideEncryption='aws:kms',
            SSEKMSKeyId=kms_key_arn
        )
        upload_id = response['UploadId']
        print(f"Initiated upload (ID: {upload_id})")

        part_size = 8 * 1024 * 1024
        file_size = os.path.getsize(file_path)
        part_count = math.ceil(file_size / part_size)
        parts = []

        with open(file_path, 'rb') as f:
            for i in range(1, part_count + 1):
                print(f"Uploading part {i}/{part_count}...")
                offset = part_size * (i - 1)
                bytes_to_read = min(part_size, file_size - offset)
                f.seek(offset)
                data = f.read(bytes_to_read)

                response = s3_client.upload_part(
                    Bucket=bucket_name,
                    Key=file_name,
                    PartNumber=i,
                    UploadId=upload_id,
                    Body=data
                )
                parts.append({'PartNumber': i, 'ETag': response['ETag']})

        s3_client.complete_multipart_upload(
            Bucket=bucket_name,
            Key=file_name,
            UploadId=upload_id,
            MultipartUpload={'Parts': parts}
        )
        print(f"Upload completed successfully! s3://{bucket_name}/{file_name}")

        return generate_presigned_url(s3_client, bucket_name, file_name, url_expiry_hours)

    except Exception as e:
        print(f"Upload failed: {str(e)}")
        if 'upload_id' in locals():
            s3_client.abort_multipart_upload(
                Bucket=bucket_name,
                Key=file_name,
                UploadId=upload_id
            )
            print("Aborted incomplete upload")
        sys.exit(1)

def main():
    print("=== AWS S3 Secure Upload Setup ===")
    config = validate_config()
    s3_client = create_s3_client(config)

    try:
        s3_client.head_bucket(Bucket=config['bucket'])
        print(f"Verified access to bucket: {config['bucket']}")
    except ClientError as e:
        print(f"Bucket access failed: {e.response['Error']['Message']}")
        sys.exit(1)

    if len(sys.argv) < 2:
        print("Usage: ./run_upload.sh <file_path>")
        sys.exit(1)

    file_path = sys.argv[1]
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        sys.exit(1)

    presigned_url = multipart_upload(
        s3_client=s3_client,
        file_path=file_path,
        bucket_name=config['bucket'],
        kms_key_arn=config['kms_key'],
        url_expiry_hours=config['url_expiry_hours']
    )

    if presigned_url:
        return presigned_url

if __name__ == "__main__":
    main()

# #!/usr/bin/env python3
# import boto3
# import os
# import sys
# import math
# from botocore.exceptions import ClientError
#
# def debug_print_credentials():
#     """Show current AWS credentials being used"""
#     session = boto3.Session()
#     credentials = session.get_credentials()
#
#     print("\n=== AWS Credentials Debug ===")
#     print(f"Using profile: {session.profile_name or 'default'}")
#     if credentials:
#         masked_key = credentials.access_key[:4] + '...' + credentials.access_key[-4:]
#         print(f"Access key: {masked_key}")
#         print(f"Region: {session.region_name}")
#     else:
#         print("No credentials found!")
#     print("===========================\n")
#
# def validate_config():
#     """Validate all required environment variables"""
#     required_vars = {
#         'S3_BUCKET_NAME': os.getenv('S3_BUCKET_NAME'),
#         'AWS_KMS_KEY_ARN': os.getenv('AWS_KMS_KEY_ARN'),
#         'ADMIN_ACCESS_KEY': os.getenv('ADMIN_ACCESS_KEY'),
#         'ADMIN_SECRET_KEY': os.getenv('ADMIN_SECRET_KEY')
#     }
#
#     missing = [k for k, v in required_vars.items() if not v]
#     if missing:
#         print(f"❌ Missing environment variables: {', '.join(missing)}")
#         sys.exit(1)
#
#     return {
#         'bucket': required_vars['S3_BUCKET_NAME'],
#         'kms_key': required_vars['AWS_KMS_KEY_ARN'],
#         'access_key': required_vars['ADMIN_ACCESS_KEY'],
#         'secret_key': required_vars['ADMIN_SECRET_KEY']
#     }
#
# def create_s3_client(config):
#     """Create authenticated S3 client"""
#     try:
#         session = boto3.Session(
#             aws_access_key_id=config['access_key'],
#             aws_secret_access_key=config['secret_key'],
#             region_name=os.getenv('AWS_REGION', 'us-east-1')
#         )
#
#         # Verify credentials work
#         sts = session.client('sts')
#         identity = sts.get_caller_identity()
#         print(f"✅ Authenticated as: {identity['Arn']}")
#
#         return session.client('s3')
#     except ClientError as e:
#         print(f"🚨 Authentication failed: {e.response['Error']['Message']}")
#         sys.exit(1)
#
# def multipart_upload(file_path, bucket_name, kms_key_arn):
#     """Handle multipart upload with KMS encryption"""
#     s3 = boto3.client('s3')
#     file_name = os.path.basename(file_path)
#
#     try:
#         # 1. Initialize multipart upload
#         response = s3.create_multipart_upload(
#             Bucket=bucket_name,
#             Key=file_name,
#             ServerSideEncryption='aws:kms',
#             SSEKMSKeyId=kms_key_arn
#         )
#         upload_id = response['UploadId']
#         print(f"ℹ️ Initiated upload (ID: {upload_id})")
#
#         # 2. Upload parts
#         part_size = 8 * 1024 * 1024  # 8MB chunks
#         file_size = os.path.getsize(file_path)
#         part_count = math.ceil(file_size / part_size)
#         parts = []
#
#         with open(file_path, 'rb') as f:
#             for i in range(1, part_count + 1):
#                 print(f"📤 Uploading part {i}/{part_count}...")
#                 offset = part_size * (i - 1)
#                 bytes_to_read = min(part_size, file_size - offset)
#                 f.seek(offset)
#                 data = f.read(bytes_to_read)
#
#                 response = s3.upload_part(
#                     Bucket=bucket_name,
#                     Key=file_name,
#                     PartNumber=i,
#                     UploadId=upload_id,
#                     Body=data
#                 )
#                 parts.append({
#                     'PartNumber': i,
#                     'ETag': response['ETag']
#                 })
#
#         # 3. Complete upload
#         s3.complete_multipart_upload(
#             Bucket=bucket_name,
#             Key=file_name,
#             UploadId=upload_id,
#             MultipartUpload={'Parts': parts}
#         )
#         print(f"✅ Upload completed successfully! s3://{bucket_name}/{file_name}")
#
#     except Exception as e:
#         print(f"🚨 Upload failed: {str(e)}")
#         if 'upload_id' in locals():
#             s3.abort_multipart_upload(
#                 Bucket=bucket_name,
#                 Key=file_name,
#                 UploadId=upload_id
#             )
#             print("⚠️ Aborted incomplete upload")
#         sys.exit(1)
#
# def main():
#     print("=== AWS S3 Secure Upload Setup ===")
#     debug_print_credentials()
#
#     config = validate_config()
#     s3 = create_s3_client(config)
#
#     # Verify bucket access
#     try:
#         s3.head_bucket(Bucket=config['bucket'])
#         print(f"✅ Verified access to bucket: {config['bucket']}")
#     except ClientError as e:
#         print(f"🚨 Bucket access failed: {e.response['Error']['Message']}")
#         sys.exit(1)
#
#     # Handle file upload
#     if len(sys.argv) < 2:
#         print("Usage: ./run_upload.sh <file_path>")
#         sys.exit(1)
#
#     file_path = sys.argv[1]
#     if not os.path.exists(file_path):
#         print(f"❌ File not found: {file_path}")
#         sys.exit(1)
#
#     multipart_upload(
#         file_path=file_path,
#         bucket_name=config['bucket'],
#         kms_key_arn=config['kms_key']
#     )
#
# if __name__ == "__main__":
#     main()
# # #!/usr/bin/env python3
# # import boto3
# # import os
# # import sys
# # from datetime import datetime, timedelta
# # from botocore.exceptions import ClientError, NoCredentialsError
#
# # # Configuration - Load from environment variables
# # BUCKET_NAME = os.getenv('S3_BUCKET_NAME')
# # KMS_KEY_ARN = os.getenv('AWS_KMS_KEY_ARN')
# # ALLOWED_USERS = [
# #     os.getenv('ADMIN_USER_ARN'),  # Set these in your environment
# #     os.getenv('EDITOR_USER_ARN')  # or replace with actual ARNs
# # ]
#
# # def verify_uploader_identity():
# #     """Verify the AWS user matches our Terraform-created users"""
# #     sts = boto3.client('sts')
# #     try:
# #         identity = sts.get_caller_identity()
#
# #         if identity['Arn'] not in ALLOWED_USERS:
# #             print(f"❌ ERROR: Unauthorized user: {identity['Arn']}")
# #             print("Allowed users:")
# #             for user in ALLOWED_USERS:
# #                 print(f" - {user}")
# #             sys.exit(1)
#
# #         print(f"✅ Verified identity: {identity['Arn']}")
# #         return identity
#
# #     except (ClientError, NoCredentialsError) as e:
# #         print(f"🚨 AWS Authentication Error: {str(e)}")
# #         sys.exit(1)
# # if __name__ == "__main__":
# #     # Check environment variables
# #     if not all([BUCKET_NAME, KMS_KEY_ARN, all(ALLOWED_USERS)]):
# #         print("Missing required environment variables:")
# #         print(" - S3_BUCKET_NAME")
# #         print(" - AWS_KMS_KEY_ARN")
# #         print(" - ADMIN_USER_ARN")
# #         print(" - EDITOR_USER_ARN")
# #         sys.exit(1)
#
# #     if len(sys.argv) < 2:
# #         print(f"Usage: {sys.argv[0]} <file_path> [expiry_hours]")
# #         sys.exit(1)
#
# #     file_path = sys.argv[1]
# #     expires_hours = int(sys.argv[2]) if len(sys.argv) > 2 else 1
#
# #     result = secure_upload(file_path, expires_hours)
#
# #     print("\n🔗 Presigned URL (expires at {}):".format(result['expires_at']))
# #     print(result['url'])
# #     print("\nℹ️ Object Key:", result['object_key'])
#
# # # def multipart_upload(file_path, bucket, key, credentials, chunk_size=DEFAULT_CHUNK_SIZE):
# # #     s3 = boto3.client(
# # #         's3',
# # #         aws_access_key_id=credentials['AccessKeyId'],
# # #         aws_secret_access_key=credentials['SecretAccessKey'],
# # #         aws_session_token=credentials['SessionToken']
# # #     )
#
# # #     file_size = os.path.getsize(file_path)
# # #     chunks_count = math.ceil(file_size / chunk_size)
#
# # #     # Initiate multipart upload
# # #     mpu = s3.create_multipart_upload(
# # #         Bucket=bucket,
# # #         Key=key,
# # #         ServerSideEncryption='aws:kms',
# # #         SSEKMSKeyId=credentials.get('kms_key_arn', None)
# # #     )
# # #     mpu_id = mpu['UploadId']
#
# # #     parts = []
# # #     try:
# # #         with open(file_path, 'rb') as f:
# # #             for i in range(1, chunks_count + 1):
# # #                 print(f"Uploading part {i}/{chunks_count}")
# # #                 offset = chunk_size * (i - 1)
# # #                 bytes_to_read = min(chunk_size, file_size - offset)
# # #                 f.seek(offset)
#
# # #                 part = s3.upload_part(
# # #                     Bucket=bucket,
# # #                     Key=key,
# # #                     PartNumber=i,
# # #                     UploadId=mpu_id,
# # #                     Body=f.read(bytes_to_read)
# # #                 parts.append({'PartNumber': i, 'ETag': part['ETag']})
#
# # #         # Complete the upload
# # #         result = s3.complete_multipart_upload(
# # #             Bucket=bucket,
# # #             Key=key,
# # #             UploadId=mpu_id,
# # #             MultipartUpload={'Parts': parts}
# # #         )
# # #         return result['Location']
#
# # #     except Exception as e:
# # #         print(f"Error during upload: {e}")
# # #         s3.abort_multipart_upload(
# # #             Bucket=bucket,
# # #             Key=key,
# # #             UploadId=mpu_id
# # #         )
# # #         raise
#
# # # def main():
# # #     parser = argparse.ArgumentParser()
# # #     parser.add_argument("file", help="File to upload")
# # #     parser.add_argument("--bucket", required=True)
# # #     parser.add_argument("--role-arn", required=True)
# # #     parser.add_argument("--expiry", type=int, default=72)
# # #     parser.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE)
# # #     args = parser.parse_args()
#
# # #     # Assume role with longer duration
# # #     sts = boto3.client('sts')
# # #     creds = sts.assume_role(
# # #         RoleArn=args.role_arn,
# # #         RoleSessionName='s3-multipart-upload',
# # #         DurationSeconds=3600 * 3  # 3 hour session for large files
# # #     )['Credentials']
#
# # #     # Upload file
# # #     key = os.path.basename(args.file)
# # #     try:
# # #         upload_location = multipart_upload(
# # #             args.file,
# # #             args.bucket,
# # #             key,
# # #             creds,
# # #             args.chunk_size
# # #         )
# # #         print(f"Successfully uploaded to {upload_location}")
#
# # #         # Generate pre-signed URL
# # #         s3 = boto3.client(
# # #             's3',
# # #             aws_access_key_id=creds['AccessKeyId'],
# # #             aws_secret_access_key=creds['SecretAccessKey'],
# # #             aws_session_token=creds['SessionToken']
# # #         )
#
# # #         url = s3.generate_presigned_url(
# # #             'get_object',
# # #             Params={'Bucket': args.bucket, 'Key': key},
# # #             ExpiresIn=args.expiry*3600
# # #         )
# # #         print(f"\nPre-signed URL (expires in {args.expiry} hours):")
# # #         print(url)
#
# # #     except Exception as e:
# # #         print(f"Upload failed: {str(e)}")
# # #         exit(1)
#
# # # if __name__ == "__main__":
# # #     main()