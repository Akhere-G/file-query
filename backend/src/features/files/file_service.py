import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from mypy_boto3_s3.client import S3Client
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from src.exceptions import BadRequestError, NotFoundError
from src.features.files.file_model import File, FileStatus, Project
from src.features.files.file_schema import ConfirmUploadRequest, FileCreate
from src.settings import settings


max_user_storage = 1024 * 1024 * 1024 * 2


def convert_storage_to_GB(value: int):
    return value / (1024 * 1024 * 1024)


max_user_storage_str = f"{convert_storage_to_GB(max_user_storage)} GB"

load_dotenv()
region_name = settings.AWS_REGION
bucket_name = settings.AWS_BUCKET_NAME


def get_s3_client() -> S3Client:
    s3_client = boto3.client(
        "s3",
        region_name=region_name,
        config=Config(signature_version="s3v4", s3={"addressing_style": "virtual"}),
    )

    return s3_client  # type: ignore


def get_files(db: Session, project_id: int):
    stmt = select(File).where(File.project_id == project_id)
    return db.execute(stmt).scalars().all()


def get_files_by_ids(db: Session, file_ids: list[int]):
    stmt = (
        select(File)
        .where(File.id.in_(file_ids))
        .options(selectinload(File.project).options(selectinload(Project.user)))
    )
    return db.execute(stmt).scalars().all()


def get_file(db: Session, file_id: int):
    stmt = select(File).where(File.id == file_id)
    file = db.execute(stmt).scalar_one_or_none()
    if not file:
        raise NotFoundError("File not found")
    return file


def view_file_content(db: Session, file_id: int, expiration=60 * 60):
    file = get_file(db, file_id)

    if file.status == FileStatus.pending:
        raise BadRequestError("File has not been uploaded yet")
    if file.status == FileStatus.error:
        raise BadRequestError(f"Cannot view file due to error: {file.error}")

    s3_client = get_s3_client()

    try:
        s3_client.head_object(Bucket=bucket_name, Key=file.storage_key)

    except ClientError:
        raise NotFoundError("File not found")

    return s3_client.generate_presigned_url(
        ClientMethod="get_object",
        Params={"Bucket": bucket_name, "Key": file.storage_key},
        ExpiresIn=expiration,
    )


def get_used_storage(db: Session, user_id: int):
    stmt = (
        select(File)
        .join(Project, File.project_id == Project.id)
        .where(Project.user_id == user_id)
        .where(File.status.in_([FileStatus.processing, FileStatus.processed]))
    )
    files = db.execute(stmt).scalars().all()
    return sum([file.size for file in files])


def create_file(db: Session, project_id: int, file_in: FileCreate):
    new_file = File(
        name=file_in.name,
        mime_type=file_in.mime_type,
        size=file_in.size,
        project_id=project_id,
        storage_key=File.create_storage_key(project_id),
    )
    db.add(new_file)
    db.commit()
    return new_file


def create_files(
    db: Session, user_id: int, project_id: int, files_in: list[FileCreate]
):
    res: list[File] = []
    used_storage = get_used_storage(db, user_id)
    upload_size = 0

    for file in files_in:
        new_file = File(
            name=file.name,
            mime_type=file.mime_type,
            size=file.size,
            project_id=project_id,
            storage_key=File.create_storage_key(project_id),
        )
        upload_size += file.size

        if (used_storage + upload_size) > max_user_storage:
            raise BadRequestError(
                f"You can only upload a maximum of {max_user_storage_str}. You have used {convert_storage_to_GB(used_storage)} GB. Delete unused files to upload more."
            )
        res.append(new_file)
    db.add_all(res)
    db.commit()
    return res


def get_presigned_post(files: list[File], expiration: int | None = 60 * 15):
    expiration = expiration or (60 * 15)
    s3_client = get_s3_client()
    urls = []
    try:
        for file in files:
            post = s3_client.generate_presigned_post(
                Bucket=bucket_name,
                Key=file.storage_key,
                Fields={
                    "Content-Type": file.mime_type,
                },
                Conditions=[
                    {"Content-Type": file.mime_type},
                    ["content-length-range", file.size, file.size],
                ],
                ExpiresIn=expiration,
            )
            urls.append(
                {
                    "id": file.id,
                    "key": file.storage_key,
                    "url": post["url"],
                    "fields": post["fields"],
                }
            )
        return urls
    except ClientError as e:
        print(e)
        raise


def confirm_uploads(
    db: Session, user_id: int, confirmed_files: list[ConfirmUploadRequest]
):
    files = get_files_by_ids(db, [file.id for file in confirmed_files])
    errors = {file.id: file.error for file in confirmed_files if file.error}
    successful_uploads: list[File] = []
    s3_client = get_s3_client()
    used_storage = get_used_storage(db, user_id)
    for file in files:
        if file.status != FileStatus.pending:
            db.rollback()
            raise BadRequestError("File already uploaded")
        if file.id in errors:
            file.error = errors[file.id]
            file.status = FileStatus.error
        else:
            try:
                res = s3_client.head_object(Bucket=bucket_name, Key=file.storage_key)
                file_size = res["ContentLength"]
                if (file_size + used_storage) > max_user_storage:
                    file.status = FileStatus.error
                    file.error = "You have ran out of storage. Delete files to add more"
                    s3_client.delete_object(Bucket=bucket_name, Key=file.storage_key)
                    break
                used_storage += file_size

                file.status = FileStatus.processing
                successful_uploads.append(file)
                file.size = file_size
            except ClientError:
                file.status = FileStatus.error
                file.error = "File not found on storage"

    db.commit()
    return successful_uploads


def delete_file(db: Session, file_id: int):
    file = get_file(db, file_id)
    storage_key = file.storage_key
    status = file.status
    db.delete(file)
    db.commit()
    if status in [FileStatus.processing, FileStatus.processed]:
        s3_client = get_s3_client()
        s3_client.delete_object(Bucket=bucket_name, Key=storage_key)

    return file_id
