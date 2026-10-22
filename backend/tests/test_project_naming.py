from tests.helpers import upload_and_confirm


def project_name(client, headers, project_id):
    return client.get(f"/api/projects/{project_id}", headers=headers).json()["name"]


def test_new_project_gets_an_ai_name(client, make_user, aws_fakes):
    _, headers = make_user()
    aws_fakes.bedrock.answer = "Banana Baking Guide"
    project_id, _, _ = upload_and_confirm(
        client, aws_fakes, headers, "notes.txt", b"banana bread needs ripe bananas"
    )
    assert project_name(client, headers, project_id) == "Banana Baking Guide"


def test_user_chosen_name_is_not_overwritten_by_later_uploads(client, make_user, aws_fakes):
    _, headers = make_user()
    project_id, _, _ = upload_and_confirm(
        client, aws_fakes, headers, "one.txt", b"first document text"
    )
    client.patch(f"/api/projects/{project_id}", json={"name": "My recipes"}, headers=headers)

    aws_fakes.bedrock.answer = "Some Other Name"
    upload_and_confirm(
        client, aws_fakes, headers, "two.txt", b"second document text", project_id=project_id
    )
    assert project_name(client, headers, project_id) == "My recipes"
