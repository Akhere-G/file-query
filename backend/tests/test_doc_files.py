from tests.helpers import upload_and_confirm


def test_unreadable_doc_ends_in_error(client, make_user, aws_fakes):
    _, headers = make_user()
    project_id, _, _ = upload_and_confirm(
        client, aws_fakes, headers, "letter.doc", b"not a word document", "application/msword"
    )
    file = client.get(f"/api/projects/{project_id}/files", headers=headers).json()[0]
    assert file["status"] == "error"
