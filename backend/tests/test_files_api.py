import pytest

from src.features.chat.message_model import Citation, Message, MessageOwner
from src.features.files.file_model import Chunk, File, FileStatus, Project
from tests.helpers import add_file_with_chunks, add_project, upload_and_confirm


def request_upload(client, headers, files, project_id=None):
    url = "/api/files" + (f"?project_id={project_id}" if project_id else "")
    return client.post(url, json=files, headers=headers)


@pytest.fixture
def user(make_user):
    return make_user()


@pytest.fixture
def headers(user):
    return user[1]


class TestPresignedUpload:
    def test_upload_url_is_pinned_to_the_declared_size_and_type(self, client, aws_fakes, headers):
        res = request_upload(
            client, headers, [{"name": "a.pdf", "mimeType": "application/pdf", "size": 1234}]
        )

        assert res.status_code == 200
        (post,) = aws_fakes.s3.presigned_posts
        assert post["Conditions"] == [
            {"Content-Type": "application/pdf"},
            ["content-length-range", 1234, 1234],
        ]
        assert post["Fields"] == {"Content-Type": "application/pdf"}
        assert post["ExpiresIn"] <= 15 * 60

    def test_every_file_gets_its_own_unguessable_key_inside_its_project(self, client, aws_fakes, headers):
        res = request_upload(
            client,
            headers,
            [{"name": f"{i}.txt", "mimeType": "text/plain", "size": 5} for i in range(3)],
        )

        keys = [f["key"] for f in res.json()["files"]]
        project_id = res.json()["projectId"]
        assert len(set(keys)) == 3
        assert all(f"/projects/{project_id}/files/" in key for key in keys)

    def test_files_start_as_pending_until_the_upload_is_confirmed(self, client, db, headers):
        res = request_upload(client, headers, [{"name": "a.txt", "mimeType": "text/plain", "size": 5}])

        assert db.get(File, res.json()["files"][0]["id"]).status == FileStatus.pending

    @pytest.mark.parametrize(
        "payload",
        [
            [],
            [{"name": "a.txt", "mimeType": "text/plain"}],
            [{"name": "a.txt", "mimeType": "text/plain", "size": "big"}],
            {"name": "a.txt"},
        ],
        ids=["empty-list", "missing-size", "bad-size-type", "not-a-list"],
    )
    def test_malformed_requests_are_rejected_without_creating_anything(self, client, db, headers, payload):
        res = request_upload(client, headers, payload)

        assert res.status_code in (400, 422)
        assert db.query(File).count() == 0
        assert db.query(Project).count() == 0

    def test_unauthenticated_requests_are_rejected(self, client):
        res = client.post("/api/files", json=[{"name": "a.txt", "mimeType": "text/plain", "size": 5}])
        assert res.status_code == 401


class TestConfirm:
    def test_confirming_a_file_that_was_never_uploaded_marks_it_as_an_error(self, client, db, headers):
        file = request_upload(
            client, headers, [{"name": "a.txt", "mimeType": "text/plain", "size": 5}]
        ).json()["files"][0]

        res = client.post("/api/files/confirm", json=[{"id": file["id"]}], headers=headers)

        assert res.status_code == 200
        stored = db.get(File, file["id"])
        assert stored.status == FileStatus.error
        assert "not found on storage" in stored.error.lower()

    def test_a_client_reported_upload_failure_is_recorded_and_not_processed(
        self, client, db, aws_fakes, headers
    ):
        file = request_upload(
            client, headers, [{"name": "a.txt", "mimeType": "text/plain", "size": 5}]
        ).json()["files"][0]
        aws_fakes.s3.put(file["key"], b"hello")

        client.post(
            "/api/files/confirm",
            json=[{"id": file["id"], "error": "Could not upload"}],
            headers=headers,
        )

        stored = db.get(File, file["id"])
        assert stored.status == FileStatus.error
        assert aws_fakes.bedrock.embed_calls == 0

    def test_a_file_can_only_be_confirmed_once(self, client, aws_fakes, headers):
        _, file_id, first = upload_and_confirm(client, aws_fakes, headers, "a.txt", b"hello there")
        assert first.status_code == 200

        second = client.post("/api/files/confirm", json=[{"id": file_id}], headers=headers)

        assert second.status_code == 400
        assert aws_fakes.bedrock.embed_calls == 1  # not processed a second time

    def test_a_request_mixing_own_and_foreign_files_changes_nothing(
        self, client, db, aws_fakes, headers, make_user
    ):
        own = request_upload(client, headers, [{"name": "a.txt", "mimeType": "text/plain", "size": 5}]).json()["files"][0]
        _, other_headers = make_user()
        foreign = request_upload(
            client, other_headers, [{"name": "b.txt", "mimeType": "text/plain", "size": 5}]
        ).json()["files"][0]
        aws_fakes.s3.put(own["key"], b"hello")
        aws_fakes.s3.put(foreign["key"], b"hello")

        res = client.post(
            "/api/files/confirm", json=[{"id": own["id"]}, {"id": foreign["id"]}], headers=headers
        )

        assert res.status_code == 404
        assert db.get(File, own["id"]).status == FileStatus.pending
        assert db.get(File, foreign["id"]).status == FileStatus.pending

    def test_unknown_file_ids_are_a_404(self, client, headers):
        assert client.post("/api/files/confirm", json=[{"id": 999}], headers=headers).status_code == 404


class TestViewingAndDeleting:
    def test_viewing_a_processed_file_returns_a_temporary_link(self, client, aws_fakes, headers):
        _, file_id, _ = upload_and_confirm(client, aws_fakes, headers, "a.txt", b"hello there")

        res = client.get(f"/api/files/{file_id}", headers=headers)

        assert res.status_code == 200
        assert res.json()["file"]["name"] == "a.txt"
        assert res.json()["url"].startswith("https://")
        assert "storageKey" not in res.json()["file"]

    def test_a_file_that_is_not_uploaded_yet_cannot_be_viewed(self, client, headers):
        file = request_upload(client, headers, [{"name": "a.txt", "mimeType": "text/plain", "size": 5}]).json()["files"][0]
        assert client.get(f"/api/files/{file['id']}", headers=headers).status_code == 400

    def test_a_file_in_error_cannot_be_viewed(self, client, aws_fakes, headers):
        _, file_id, _ = upload_and_confirm(
            client, aws_fakes, headers, "bad.pdf", b"not a pdf", "application/pdf"
        )
        res = client.get(f"/api/files/{file_id}", headers=headers)
        assert res.status_code == 400
        assert "error" in res.json()["detail"].lower()

    def test_a_file_missing_from_storage_is_a_404(self, client, aws_fakes, headers):
        _, file_id, _ = upload_and_confirm(client, aws_fakes, headers, "a.txt", b"hello there")
        aws_fakes.s3.objects.clear()
        assert client.get(f"/api/files/{file_id}", headers=headers).status_code == 404

    def test_deleting_a_file_removes_its_chunks_and_storage_object(self, client, db, aws_fakes, headers):
        _, file_id, _ = upload_and_confirm(client, aws_fakes, headers, "a.txt", b"hello there")
        key = db.get(File, file_id).storage_key
        assert db.query(Chunk).filter_by(file_id=file_id).count() == 1

        assert client.delete(f"/api/files/{file_id}", headers=headers).status_code in (200, 204)

        db.expire_all()
        assert db.get(File, file_id) is None
        assert db.query(Chunk).filter_by(file_id=file_id).count() == 0
        assert key in aws_fakes.s3.deleted

    def test_deleting_a_cited_file_keeps_the_conversation_but_drops_the_citation(
        self, client, db, aws_fakes, headers
    ):
        project_id, file_id, _ = upload_and_confirm(client, aws_fakes, headers, "a.txt", b"hello there")
        answer = client.post(
            f"/api/projects/{project_id}/messages", json={"content": "hello"}, headers=headers
        ).json()
        assert answer["citations"]

        client.delete(f"/api/files/{file_id}", headers=headers)

        db.expire_all()
        assert db.query(Citation).count() == 0
        assert db.query(Message).filter_by(owner=MessageOwner.assistant).count() == 1


class TestDatabaseIntegrity:
    def test_storage_keys_are_unique(self, db, make_user):
        import sqlalchemy

        user, _ = make_user()
        project_id = add_project(db, user["id"])
        first, _ = add_file_with_chunks(db, project_id, ["one"])
        duplicate = File(
            name="dup.md",
            mime_type="text/markdown",
            size=1,
            storage_key=db.get(File, first).storage_key,
            project_id=project_id,
        )
        db.add(duplicate)
        with pytest.raises(sqlalchemy.exc.IntegrityError):
            db.commit()
        db.rollback()

    def test_embeddings_must_have_1024_dimensions(self, db, make_user):
        import sqlalchemy

        user, _ = make_user()
        file_id, _ = add_file_with_chunks(db, add_project(db, user["id"]), ["one"])
        db.add(Chunk(file_id=file_id, content="short vector", embedding=[0.1, 0.2]))
        with pytest.raises(sqlalchemy.exc.StatementError):
            db.commit()
        db.rollback()

    def test_a_chunk_cannot_belong_to_a_missing_file(self, db):
        import sqlalchemy

        db.add(Chunk(file_id=424242, content="orphan"))
        with pytest.raises(sqlalchemy.exc.IntegrityError):
            db.commit()
        db.rollback()
