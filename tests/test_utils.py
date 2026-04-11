import json

from utils.file_manager_util import (add_contributor, add_user, create_project,
                                     get_project_owner, get_user_projects,
                                     setup_start)


def TestSetup_Start(tmp_path):
    assert setup_start(tmp_path) is True

    projects_dir = tmp_path / "user_projects"
    index_file = projects_dir / "projects_index.json"

    assert projects_dir.exists()
    assert projects_dir.is_dir()
    assert index_file.exists()
    assert index_file.is_file()

    tests_dir = tmp_path / "user_tests"

    assert tests_dir.exists()
    assert tests_dir.is_dir()

    deployed_dir = tmp_path / "deployed_projects"

    assert deployed_dir.exists()
    assert deployed_dir.is_dir()


def TestAdd_User(tmp_path):

    setup_start(tmp_path)

    assert add_user(tmp_path, "test_username1") is True
    assert add_user(tmp_path, "test_username2") is True

    projects_dir = tmp_path / "user_projects"

    user1_folder = projects_dir / "test_username1"

    assert user1_folder.exists()
    assert user1_folder.is_dir()

    user2_folder = projects_dir / "test_username2"

    assert user2_folder.exists()
    assert user2_folder.is_dir()

    index_data = json.loads((projects_dir / "projects_index.json").read_text())
    assert index_data["users"]["test_username1"] == []
    assert index_data["users"]["test_username2"] == []


def TestCreate_project(tmp_path):
    setup_start(tmp_path)

    add_user(tmp_path, "test_username1")
    add_user(tmp_path, "test_username2")

    assert create_project(tmp_path, "test_username1", "test_project1", True) is True
    assert create_project(tmp_path, "test_username2", "test_project2", False) is True

    p1 = tmp_path / "user_projects" / "test_username1" / "test_project1"
    p2 = tmp_path / "user_projects" / "test_username2" / "test_project2"

    assert p1.is_dir()
    assert p2.is_dir()

    for p in [p1, p2]:
        assert (p / "settings.txt").is_file()
        assert (p / "files").is_dir()
        assert (p / "issues").is_dir()
        assert (p / "history").is_dir()

    data1 = json.loads((p1 / "settings.txt").read_text())
    data2 = json.loads((p2 / "settings.txt").read_text())

    assert data1["owner"] == "test_username1"
    assert data1["project_name"] == "test_project1"
    assert data1["private"] is True
    assert "contributors" in data1

    assert data2["owner"] == "test_username2"
    assert data2["project_name"] == "test_project2"
    assert data2["private"] is False
    assert "contributors" in data1

    index_data = json.loads(
        (tmp_path / "user_projects" / "projects_index.json").read_text()
    )
    assert index_data["users"]["test_username1"] == ["test_project1"]
    assert index_data["users"]["test_username2"] == ["test_project2"]
    assert (
        index_data["projects"]["test_username1/test_project1"]["owner"]
        == "test_username1"
    )
    assert (
        index_data["projects"]["test_username2/test_project2"]["owner"]
        == "test_username2"
    )
    assert index_data["project_names"]["test_project1"] == ["test_username1"]
    assert index_data["project_names"]["test_project2"] == ["test_username2"]


def TestAdd_Contributor(tmp_path):
    setup_start(tmp_path)
    add_user(tmp_path, "test_username1")
    add_user(tmp_path, "test_username2")
    create_project(tmp_path, "test_username1", "test_project1", True)

    assert add_contributor(
        tmp_path, "test_username2", "test_project1", "test_username1"
    )

    project_path = tmp_path / "user_projects" / "test_username1" / "test_project1"
    settings_file = project_path / "settings.txt"

    with open(settings_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "test_username2" in data["contributors"]


def test_project_index_helpers(tmp_path):
    setup_start(tmp_path)
    add_user(tmp_path, "test_username1")
    add_user(tmp_path, "test_username2")
    create_project(tmp_path, "test_username1", "shared_name", True)
    create_project(tmp_path, "test_username2", "shared_name", False)
    create_project(tmp_path, "test_username1", "solo_project", True)

    assert get_user_projects(tmp_path, "test_username1") == [
        "shared_name",
        "solo_project",
    ]
    assert get_user_projects(tmp_path, "test_username2") == ["shared_name"]
    assert get_user_projects(tmp_path, "missing_user") == []

    assert get_project_owner(tmp_path, "solo_project") == "test_username1"
    assert get_project_owner(tmp_path, "shared_name") == [
        "test_username1",
        "test_username2",
    ]
    assert (
        get_project_owner(tmp_path, "shared_name", owner="test_username2")
        == "test_username2"
    )
    assert get_project_owner(tmp_path, "missing_project") is None
