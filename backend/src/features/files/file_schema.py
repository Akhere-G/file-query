from pydantic import field_validator, model_validator
from src.features.files.file_model import FileStatus
from src.schemas import BaseModel
from src.settings import settings

MAX_FILE_SIZE = settings.MAX_FILE_SIZE
MAX_USER_STORAGE = settings.MAX_USER_STORAGE

# MIME type -> accepted file extensions. The frontend derives the type from the extension.
accepted_mime_types = {
    "application/msword": (".doc",),
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": (".docx",),
    "text/plain": (".txt",),
    "application/pdf": (".pdf",),
    "text/csv": (".csv",),
    "text/markdown": (".md", ".markdown"),
}


class FileBase(BaseModel):
    name: str
    mime_type: str
    size: int

    @field_validator("size")
    @classmethod
    def validate_size(cls, v):
        if v <= 0:
            raise ValueError("Files cannot be empty")
        if v >= MAX_FILE_SIZE:
            raise ValueError(
                f"Files must be smaller than {MAX_FILE_SIZE // (1024 * 1024)} MB"
            )
        return v

    @field_validator("mime_type")
    @classmethod
    def validate_mime_type(cls, v):
        if v not in accepted_mime_types:
            raise ValueError(
                "Files must be one of "
                + ", ".join(ext[0] for ext in accepted_mime_types.values())
            )
        return v


class FileCreate(FileBase):
    @field_validator("name")
    @classmethod
    def clean_name(cls, v: str):
        name = v.replace("\\", "/").split("/")[-1].strip()
        if not name or len(name) > 255:
            raise ValueError("File names must be 1 to 255 characters")
        return name

    @model_validator(mode="after")
    def extension_matches_type(self):
        if not self.name.lower().endswith(accepted_mime_types[self.mime_type]):
            raise ValueError(
                f"{self.name} does not look like a "
                f"{accepted_mime_types[self.mime_type][0]} file"
            )
        return self


class FileResponse(FileBase):
    id: int
    error: str | None
    project_id: int
    status: FileStatus


class ConfirmUploadRequest(BaseModel):
    id: int
    error: str | None = None


class ChunkResponse(BaseModel):
    id: int
    file_id: int
    content: str
    title: str | None = None
    file_name: str

    @model_validator(mode="before")
    @classmethod
    def flatten_filename(cls, data):
        if isinstance(data, dict):
            if "file" in data:
                data["file_name"] = data["file"].name
        elif hasattr(data, "file"):
            return {
                "id": data.id,
                "file_id": data.file_id,
                "content": data.content,
                "title": data.title,
                "fileName": data.file.name,
            }

        return data
