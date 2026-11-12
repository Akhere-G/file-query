import pytest

from src.features.chat.message_model import Citation, Message
from src.features.files.file_model import Chunk, File, Project
from tests.helpers import add_file_with_chunks, add_project, upload_and_confirm


@pytest.fixture
def user(make_user):
    return make_user()


class TestRename:
    @pytest.mark.parametrize("name", ["", "   ", "x" * 256])
    def test_invalid_names_are_rejected_and_the_name_is_unchanged(self, client, db, user, name):
        me, headers = user
        project_id = add_project(db, me["id"], "Original")

        res = client.patch(f"/api/projects/{project_id}", json={"name": name}, headers=headers)

        assert res.status_code == 400
        db.expire_all()
        assert db.get(Project, project_id).name == "Original"

    def test_names_are_trimmed(self, client, db, user):
        me, headers = user
        project_id = add_project(db, me["id"], "Original")

        res = client.patch(f"/api/projects/{project_id}", json={"name": "  Renamed  "}, headers=headers)

        assert res.status_code == 200
        assert res.json() == {"id": project_id, "name": "Renamed"}

    def test_the_longest_allowed_name_is_accepted(self, client, db, user):
        me, headers = user
        project_id = add_project(db, me["id"])
        assert client.patch(f"/api/projects/{project_id}", json={"name": "x" * 255}, headers=headers).status_code == 200

    def test_missing_name_field_is_a_validation_error(self, client, db, user):
        me, headers = user
        project_id = add_project(db, me["id"])
        assert client.patch(f"/api/projects/{project_id}", json={}, headers=headers).status_code == 422


class TestListingAndIsolation:
    def test_each_user_only_sees_their_own_projects(self, client, db, make_user):
        alice, alice_headers = make_user()
        bob, bob_headers = make_user()
        alice_project = add_project(db, alice["id"], "Alice's")
        bob_project = add_project(db, bob["id"], "Bob's")

        assert [p["id"] for p in client.get("/api/projects", headers=alice_headers).json()] == [alice_project]
        assert [p["id"] for p in client.get("/api/projects", headers=bob_headers).json()] == [bob_project]

    def test_file_listings_never_include_other_projects_files(self, client, db, user):
        me, headers = user
        first = add_project(db, me["id"])
        second = add_project(db, me["id"])
        add_file_with_chunks(db, first, ["one"], name="first.md")
        add_file_with_chunks(db, second, ["two"], name="second.md")

        names = [f["name"] for f in client.get(f"/api/projects/{first}/files", headers=headers).json()]

        assert names == ["first.md"]

    def test_listing_requires_authentication(self, client):
        assert client.get("/api/projects").status_code == 401


class TestDeleting:
    def test_deleting_a_project_removes_everything_that_belongs_to_it(self, client, db, aws_fakes, user):
        _, headers = user
        project_id, file_id, _ = upload_and_confirm(client, aws_fakes, headers, "a.txt", b"hello there")
        client.post(f"/api/projects/{project_id}/messages", json={"content": "hello"}, headers=headers)
        key = db.get(File, file_id).storage_key
        assert db.query(Citation).count() == 1

        res = client.delete(f"/api/projects/{project_id}", headers=headers)

        assert res.status_code in (200, 204)
        db.expire_all()
        assert db.query(Project).count() == 0
        assert db.query(File).count() == 0
        assert db.query(Chunk).count() == 0
        assert db.query(Message).count() == 0
        assert db.query(Citation).count() == 0
        assert key in aws_fakes.s3.deleted

    def test_deleting_one_project_leaves_the_others_untouched(self, client, db, user):
        me, headers = user
        keep = add_project(db, me["id"])
        drop = add_project(db, me["id"])
        add_file_with_chunks(db, keep, ["keep me"])
        add_file_with_chunks(db, drop, ["drop me"])

        client.delete(f"/api/projects/{drop}", headers=headers)

        db.expire_all()
        assert [p.id for p in db.query(Project)] == [keep]
        assert [c.content for c in db.query(Chunk)] == ["keep me"]
