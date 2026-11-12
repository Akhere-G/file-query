import pytest
from pydantic import ValidationError

from src.features.auth.user_schema import UserCreate, UserLogin
from src.features.chat.chat_schema import MessageCreate
from src.features.files.file_schema import ConfirmUploadRequest, FileCreate
from src.settings import settings

pytestmark = pytest.mark.unit

PDF = "application/pdf"


def register(**overrides):
    return UserCreate(**{"username": "Ada", "email": "ada@example.com", "password": "Passw0rdTest", **overrides})


class TestPasswordRules:
    @pytest.mark.parametrize(
        "password, message",
        [
            ("Sh0rt", "at least 8"),
            ("alllowercase1", "uppercase"),
            ("ALLUPPERCASE1", "lowercase"),
            ("NoDigitsHere", "digit"),
            ("A1" + "a" * 127, "at most 128"),
        ],
    )
    def test_weak_passwords_are_rejected(self, password, message):
        with pytest.raises(ValidationError, match=message):
            register(password=password)

    @pytest.mark.parametrize("length", [8, 128])
    def test_boundary_lengths_are_accepted(self, length):
        assert register(password="Aa1" + "x" * (length - 3)).password


class TestEmail:
    @pytest.mark.parametrize("email", ["not-an-email", "a@", "@b.com", "", "a b@c.com"])
    def test_invalid_emails_are_rejected(self, email):
        with pytest.raises(ValidationError):
            register(email=email)

    def test_email_is_normalised_to_lower_case(self):
        assert register(email="Ada@Example.COM").email == "ada@example.com"
        assert UserLogin(email="  Ada@Example.COM ", password="x").email == "ada@example.com"


class TestMessages:
    def test_content_is_trimmed(self):
        assert MessageCreate(content="  hello  ").content == "hello"

    @pytest.mark.parametrize("content", ["", "   \n\t "])
    def test_blank_questions_are_rejected(self, content):
        with pytest.raises(ValidationError):
            MessageCreate(content=content)

    def test_length_boundary(self):
        assert MessageCreate(content="x" * 2000)
        with pytest.raises(ValidationError):
            MessageCreate(content="x" * 2001)


class TestFileCreate:
    def make(self, **overrides):
        return FileCreate(**{"name": "report.pdf", "mimeType": PDF, "size": 100, **overrides})

    def test_valid_file(self):
        assert self.make().name == "report.pdf"

    @pytest.mark.parametrize(
        "name, mime",
        [
            ("report.txt", PDF),
            ("report", PDF),
            ("report.pdf.exe", PDF),
            ("report.PDF.zip", PDF),
            ("notes.md", "text/plain"),
        ],
    )
    def test_extension_must_match_the_declared_mime_type(self, name, mime):
        with pytest.raises(ValidationError):
            self.make(name=name, mimeType=mime)

    @pytest.mark.parametrize("name, mime", [("NOTES.MD", "text/markdown"), ("a.markdown", "text/markdown")])
    def test_extension_matching_is_case_insensitive_and_accepts_aliases(self, name, mime):
        assert self.make(name=name, mimeType=mime)

    @pytest.mark.parametrize(
        "mime", ["image/png", "application/zip", "application/x-msdownload", "text/html", ""]
    )
    def test_unsupported_mime_types_are_rejected(self, mime):
        with pytest.raises(ValidationError, match="Files must be one of"):
            self.make(mimeType=mime)

    def test_name_length_boundary(self):
        assert self.make(name="a" * 251 + ".pdf")
        with pytest.raises(ValidationError):
            self.make(name="a" * 252 + ".pdf")

    @pytest.mark.parametrize("size", [0, -1])
    def test_empty_or_negative_sizes_are_rejected(self, size):
        with pytest.raises(ValidationError, match="cannot be empty"):
            self.make(size=size)

    def test_size_must_be_below_the_limit(self):
        assert self.make(size=settings.MAX_FILE_SIZE - 1)
        with pytest.raises(ValidationError, match="smaller than"):
            self.make(size=settings.MAX_FILE_SIZE)


class TestConfirmUploadRequest:
    def test_error_is_optional(self):
        assert ConfirmUploadRequest(id=1).error is None
        assert ConfirmUploadRequest(id=1, error="Could not upload").error == "Could not upload"

    @pytest.mark.parametrize("bad_id", ["abc", None, 1.5])
    def test_id_must_be_an_integer(self, bad_id):
        with pytest.raises(ValidationError):
            ConfirmUploadRequest(id=bad_id)
