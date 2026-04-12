import json

from core.app_paths import DATA_ROOT, SERVER_ROOT
from utils.repository_manager_util import (
    add_contributor,
    add_repository_project,
    add_user,
    create_repository,
    get_public_repositories,
    get_public_user_cards,
    get_repository_details,
    get_repository_owner,
    get_user_profile,
    get_user_repository_names,
    setup_start,
    update_user_profile,
)


def test_app_paths_stay_inside_server_directory():
    assert SERVER_ROOT.name == "server"
    assert DATA_ROOT == SERVER_ROOT


def TestSetup_Start(tmp_path):
    assert setup_start(tmp_path) is True

    projects_dir = tmp_path / "user_projects"
    index_file = projects_dir / "repositories_index.json"

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

    index_data = json.loads((projects_dir / "repositories_index.json").read_text())
    assert index_data["users"]["test_username1"] == []
    assert index_data["users"]["test_username2"] == []
    assert index_data["profiles"]["test_username1"]["display_name"] == "test_username1"


def TestCreate_repository(tmp_path):
    setup_start(tmp_path)

    add_user(tmp_path, "test_username1")
    add_user(tmp_path, "test_username2")

    assert (
        create_repository(
            tmp_path,
            "test_username1",
            "test_repository1",
            True,
            project_names=["server", "client"],
        )
        is True
    )
    assert (
        create_repository(
            tmp_path,
            "test_username2",
            "test_repository2",
            False,
            project_names=["api"],
        )
        is True
    )

    p1 = tmp_path / "user_projects" / "test_username1" / "test_repository1"
    p2 = tmp_path / "user_projects" / "test_username2" / "test_repository2"

    assert p1.is_dir()
    assert p2.is_dir()

    for p in [p1, p2]:
        assert (p / "settings.txt").is_file()
        assert (p / "projects").is_dir()
        assert (p / "issues").is_dir()
        assert (p / "history").is_dir()

    data1 = json.loads((p1 / "settings.txt").read_text())
    data2 = json.loads((p2 / "settings.txt").read_text())

    assert data1["owner"] == "test_username1"
    assert data1["repository_name"] == "test_repository1"
    assert data1["private"] is True
    assert [project["name"] for project in data1["projects"]] == ["server", "client"]
    assert "contributors" in data1

    assert data2["owner"] == "test_username2"
    assert data2["repository_name"] == "test_repository2"
    assert data2["private"] is False
    assert [project["name"] for project in data2["projects"]] == ["api"]
    assert "contributors" in data2

    index_data = json.loads(
        (tmp_path / "user_projects" / "repositories_index.json").read_text()
    )
    assert index_data["users"]["test_username1"] == ["test_repository1"]
    assert index_data["users"]["test_username2"] == ["test_repository2"]
    assert (
        index_data["repositories"]["test_username1/test_repository1"]["owner"]
        == "test_username1"
    )
    assert (
        index_data["repositories"]["test_username2/test_repository2"]["owner"]
        == "test_username2"
    )
    assert index_data["repository_names"]["test_repository1"] == ["test_username1"]
    assert index_data["repository_names"]["test_repository2"] == ["test_username2"]


def TestAdd_Contributor(tmp_path):
    setup_start(tmp_path)
    add_user(tmp_path, "test_username1")
    add_user(tmp_path, "test_username2")
    create_repository(
        tmp_path, "test_username1", "test_repository1", True, project_names=["server"]
    )

    assert add_contributor(
        tmp_path, "test_username2", "test_repository1", "test_username1"
    )

    repository_path = tmp_path / "user_projects" / "test_username1" / "test_repository1"
    settings_file = repository_path / "settings.txt"

    with open(settings_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "test_username2" in data["contributors"]


def test_repository_index_helpers(tmp_path):
    setup_start(tmp_path)
    add_user(tmp_path, "test_username1")
    add_user(tmp_path, "test_username2")
    create_repository(
        tmp_path, "test_username1", "shared_name", True, project_names=["server"]
    )
    create_repository(
        tmp_path, "test_username2", "shared_name", False, project_names=["client"]
    )
    create_repository(
        tmp_path, "test_username1", "solo_repository", True, project_names=["api"]
    )

    assert get_user_repository_names(tmp_path, "test_username1") == [
        "shared_name",
        "solo_repository",
    ]
    assert get_user_repository_names(tmp_path, "test_username2") == ["shared_name"]
    assert get_user_repository_names(tmp_path, "missing_user") == []

    assert get_repository_owner(tmp_path, "solo_repository") == "test_username1"
    assert get_repository_owner(tmp_path, "shared_name") == [
        "test_username1",
        "test_username2",
    ]
    assert (
        get_repository_owner(tmp_path, "shared_name", owner="test_username2")
        == "test_username2"
    )
    assert get_repository_owner(tmp_path, "missing_repository") is None

    assert (
        add_repository_project(tmp_path, "test_username1", "solo_repository", "worker")
        is True
    )
    repository = get_repository_details(tmp_path, "test_username1", "solo_repository")
    assert repository is not None
    assert repository["project_names"] == ["api", "worker"]


def test_public_helpers_and_profiles(tmp_path):
    setup_start(tmp_path)
    add_user(tmp_path, "anna", joined_at=1234)
    add_user(tmp_path, "bob", joined_at=5678)
    update_user_profile(
        tmp_path, "anna", display_name="Anna Builder", bio="Ships fast."
    )
    create_repository(
        tmp_path,
        "anna",
        "public_one",
        False,
        description="Public repository",
        project_names=["server", "client"],
    )
    create_repository(
        tmp_path,
        "anna",
        "private_one",
        True,
        description="Private repository",
        project_names=["server"],
    )
    create_repository(
        tmp_path,
        "bob",
        "public_two",
        False,
        description="Another public repository",
        project_names=["api"],
    )

    repository = get_repository_details(
        tmp_path, "anna", "public_one", increment_views=True
    )
    assert repository is not None
    assert repository["views"] == 1

    public_repositories = get_public_repositories(tmp_path)
    assert [item["repository_name"] for item in public_repositories] == [
        "public_one",
        "public_two",
    ]

    anna_profile = get_user_profile(tmp_path, "anna")
    assert anna_profile is not None
    assert anna_profile["display_name"] == "Anna Builder"
    assert anna_profile["public_repository_count"] == 1
    assert anna_profile["public_project_total"] == 2

    public_users = get_public_user_cards(tmp_path)
    assert [item["username"] for item in public_users] == ["anna", "bob"]
