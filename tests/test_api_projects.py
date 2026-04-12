from utils.repository_manager_util import (
    add_user,
    create_repository,
    get_repository_details,
    setup_start,
    update_user_profile,
)


def _register_and_login(client, username: str, password: str, now_ms: int) -> None:
    register_res = client.post(
        "/api/register",
        json={
            "username": username,
            "password": password,
            "timestamp": now_ms,
        },
    )
    assert register_res.status_code == 200

    login_res = client.post(
        "/api/login",
        json={
            "username": username,
            "password": password,
            "timestamp": now_ms,
        },
    )
    assert login_res.status_code == 200


class TestRepositoryCreation:
    def test_create_repository_returns_metadata(self, client, now_ms, data_root):
        _register_and_login(client, "maker", "Secret123", now_ms)

        res = client.post(
            "/api/repositories",
            json={
                "name": "alpha_build",
                "description": "First public test repository",
                "visibility": "public",
                "project_names": ["server", "client"],
                "timestamp": now_ms,
            },
        )

        assert res.status_code == 200
        body = res.json()
        assert body["success"] is True
        assert body["repository"]["repository_name"] == "alpha_build"
        assert body["repository"]["private"] is False
        assert body["repository"]["description"] == "First public test repository"
        assert body["repository"]["project_names"] == ["server", "client"]

        stored = get_repository_details(data_root, "maker", "alpha_build")
        assert stored is not None
        assert stored["owner"] == "maker"

    def test_profile_update_persists(self, client, now_ms):
        _register_and_login(client, "maker", "Secret123", now_ms)

        res = client.patch(
            "/api/profile",
            json={
                "display_name": "Maker Prime",
                "bio": "Builds testable things.",
            },
        )

        assert res.status_code == 200
        body = res.json()
        assert body["success"] is True
        assert body["profile"]["display_name"] == "Maker Prime"
        assert body["profile"]["bio"] == "Builds testable things."


class TestExploreAndPublicViews:
    def test_explore_returns_only_public_repositories(self, client, now_ms, data_root):
        _register_and_login(client, "maker", "Secret123", now_ms)
        client.post(
            "/api/repositories",
            json={
                "name": "public_alpha",
                "description": "Visible to everyone",
                "visibility": "public",
                "project_names": ["server", "client"],
                "timestamp": now_ms,
            },
        )
        client.post(
            "/api/repositories",
            json={
                "name": "private_alpha",
                "description": "Visible only to owner",
                "visibility": "private",
                "project_names": ["admin"],
                "timestamp": now_ms,
            },
        )

        add_user(data_root, "other_user", joined_at=now_ms)
        update_user_profile(
            data_root, "other_user", display_name="Other User", bio="Ships public work."
        )
        create_repository(
            data_root,
            "other_user",
            "public_beta",
            private=False,
            description="Another public repository",
            project_names=["api"],
        )

        res = client.get("/api/explore")

        assert res.status_code == 200
        body = res.json()
        repository_names = [
            repository["repository_name"] for repository in body["repositories"]
        ]
        assert "public_alpha" in repository_names
        assert "public_beta" in repository_names
        assert "private_alpha" not in repository_names
        assert any(user["username"] == "other_user" for user in body["users"])

    def test_user_endpoint_returns_only_public_repositories(self, client, now_ms):
        _register_and_login(client, "maker", "Secret123", now_ms)
        client.post(
            "/api/repositories",
            json={
                "name": "public_alpha",
                "description": "Visible to everyone",
                "visibility": "public",
                "project_names": ["server", "client"],
                "timestamp": now_ms,
            },
        )
        client.post(
            "/api/repositories",
            json={
                "name": "private_alpha",
                "description": "Visible only to owner",
                "visibility": "private",
                "project_names": ["admin"],
                "timestamp": now_ms,
            },
        )

        profile_res = client.get("/api/users/maker")

        assert profile_res.status_code == 200
        body = profile_res.json()
        assert body["profile"]["username"] == "maker"
        assert [
            repository["repository_name"] for repository in body["repositories"]
        ] == ["public_alpha"]

    def test_private_repository_is_hidden_from_anonymous_viewer(
        self, client, now_ms, data_root
    ):
        setup_start(data_root)
        add_user(data_root, "maker", joined_at=now_ms)
        create_repository(
            data_root,
            "maker",
            "secret_lab",
            private=True,
            description="Private test repository",
            project_names=["server"],
        )

        res = client.get("/api/repositories/maker/secret_lab")
        assert res.status_code == 404

    def test_public_repository_view_increments_views(self, client, now_ms, data_root):
        setup_start(data_root)
        add_user(data_root, "maker", joined_at=now_ms)
        create_repository(
            data_root,
            "maker",
            "public_lab",
            private=False,
            description="Public test repository",
            project_names=["server"],
        )

        before = get_repository_details(data_root, "maker", "public_lab")
        res = client.get("/api/repositories/maker/public_lab")
        after = get_repository_details(data_root, "maker", "public_lab")

        assert res.status_code == 200
        assert before is not None
        assert after is not None
        assert after["views"] == before["views"] + 1

    def test_invalid_user_identifier_returns_404(self, client):
        res = client.get("/api/users/maker!")
        assert res.status_code == 404

    def test_invalid_repository_identifier_returns_404(self, client):
        res = client.get("/api/repositories/maker/bad!repository")
        assert res.status_code == 404
