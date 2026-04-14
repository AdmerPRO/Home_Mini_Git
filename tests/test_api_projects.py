import io
import zipfile

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
    assert register_res.status_code in {200, 400}

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
        _register_and_login(client, "maker", "Secret1234", now_ms)

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
        _register_and_login(client, "maker", "Secret1234", now_ms)

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

    def test_profile_update_sanitizes_html(self, client, now_ms):
        _register_and_login(client, "maker", "Secret1234", now_ms)

        res = client.patch(
            "/api/profile",
            json={
                "display_name": "<b>Maker</b>",
                "bio": "<script>alert(1)</script>",
            },
        )

        assert res.status_code == 200
        body = res.json()
        assert body["profile"]["display_name"] == "&lt;b&gt;Maker&lt;/b&gt;"
        assert body["profile"]["bio"] == "&lt;script&gt;alert(1)&lt;/script&gt;"

    def test_profile_update_keeps_apostrophes(self, client, now_ms):
        _register_and_login(client, "maker", "Secret1234", now_ms)

        res = client.patch(
            "/api/profile",
            json={
                "display_name": "Maker's Prime",
                "bio": "I'm building tools for devs.",
                "avatar_image": "",
            },
        )

        assert res.status_code == 200
        body = res.json()
        assert body["profile"]["display_name"] == "Maker's Prime"
        assert body["profile"]["bio"] == "I'm building tools for devs."

    def test_profile_update_stores_avatar(self, client, now_ms):
        _register_and_login(client, "maker", "Secret1234", now_ms)

        res = client.patch(
            "/api/profile",
            json={
                "display_name": "Maker Prime",
                "bio": "Builds testable things.",
                "avatar_image": "data:image/png;base64,ZmFrZQ==",
            },
        )

        assert res.status_code == 200
        body = res.json()
        assert body["profile"]["avatar_image"] == "data:image/png;base64,ZmFrZQ=="

    def test_profile_update_rejects_oversized_avatar(self, client, now_ms):
        _register_and_login(client, "maker", "Secret1234", now_ms)

        res = client.patch(
            "/api/profile",
            json={
                "display_name": "Maker Prime",
                "bio": "Builds testable things.",
                "avatar_image": "data:image/png;base64," + ("A" * 60_000),
            },
        )

        assert res.status_code == 422

    def test_add_project_file_and_read_it_back(self, client, now_ms):
        _register_and_login(client, "maker", "Secret1234", now_ms)
        client.post(
            "/api/repositories",
            json={
                "name": "alpha_build",
                "description": "First public test repository",
                "visibility": "public",
                "project_names": ["server"],
                "timestamp": now_ms,
            },
        )

        save_res = client.put(
            "/api/repositories/maker/alpha_build/projects/server/file",
            json={
                "path": "src/app.py",
                "content": "print('hello')\n",
            },
        )
        assert save_res.status_code == 200
        assert save_res.json()["file"]["path"] == "src/app.py"

        list_res = client.get(
            "/api/repositories/maker/alpha_build/projects/server/files"
        )
        assert list_res.status_code == 200
        paths = [item["path"] for item in list_res.json()["files"]]
        assert "src/app.py" in paths
        assert "README.md" in paths

        read_res = client.get(
            "/api/repositories/maker/alpha_build/projects/server/file",
            params={"path": "src/app.py"},
        )
        assert read_res.status_code == 200
        assert read_res.json()["content"] == "print('hello')\n"

    def test_create_repository_rejects_invalid_project_name(self, client, now_ms):
        _register_and_login(client, "maker", "Secret1234", now_ms)

        res = client.post(
            "/api/repositories",
            json={
                "name": "alpha_build",
                "description": "First public test repository",
                "visibility": "public",
                "project_names": ["../../../etc"],
                "timestamp": now_ms,
            },
        )

        assert res.status_code == 422

    def test_add_project_and_language_stats(self, client, now_ms):
        _register_and_login(client, "maker", "Secret1234", now_ms)
        client.post(
            "/api/repositories",
            json={
                "name": "alpha_build",
                "description": "First public test repository",
                "visibility": "public",
                "project_names": ["server"],
                "timestamp": now_ms,
            },
        )

        add_project_res = client.post(
            "/api/repositories/maker/alpha_build/projects",
            json={"name": "client", "description": "Frontend app"},
        )
        assert add_project_res.status_code == 200
        assert "client" in add_project_res.json()["repository"]["project_names"]

        client.put(
            "/api/repositories/maker/alpha_build/projects/server/file",
            json={"path": "src/app.py", "content": "print('hello')\n"},
        )
        client.put(
            "/api/repositories/maker/alpha_build/projects/client/file",
            json={"path": "styles/site.css", "content": "body { color: red; }\n"},
        )
        client.put(
            "/api/repositories/maker/alpha_build/projects/client/file",
            json={"path": "index.html", "content": "<!doctype html><html></html>\n"},
        )

        stats_res = client.get("/api/repositories/maker/alpha_build/languages")
        assert stats_res.status_code == 200
        languages = [item["language"] for item in stats_res.json()["languages"]]
        assert "Python" in languages
        assert "CSS" in languages
        assert "HTML" in languages

    def test_only_contributors_can_edit_repository(self, client, now_ms):
        _register_and_login(client, "maker", "Secret1234", now_ms)
        client.post(
            "/api/repositories",
            json={
                "name": "alpha_build",
                "description": "First public test repository",
                "visibility": "private",
                "project_names": ["server"],
                "timestamp": now_ms,
            },
        )
        client.post("/api/logout")
        _register_and_login(client, "outsider", "Secret1234", now_ms)

        update_res = client.put(
            "/api/repositories/maker/alpha_build/projects/server/file",
            json={"path": "src/app.py", "content": "print('hello')\n"},
        )
        assert update_res.status_code == 403

    def test_owner_can_invite_contributor_and_contributor_can_edit(
        self, client, now_ms
    ):
        _register_and_login(client, "maker", "Secret1234", now_ms)
        client.post(
            "/api/repositories",
            json={
                "name": "alpha_build",
                "description": "First public test repository",
                "visibility": "private",
                "project_names": ["server"],
                "timestamp": now_ms,
            },
        )
        client.put(
            "/api/repositories/maker/alpha_build/projects/server/file",
            json={"path": "src/app.py", "content": "print('owner')\n"},
        )
        client.post("/api/logout")
        _register_and_login(client, "helper", "Secret1234", now_ms)
        client.post("/api/logout")
        _register_and_login(client, "maker", "Secret1234", now_ms)

        invite_res = client.post(
            "/api/repositories/maker/alpha_build/invite",
            json={"username": "helper"},
        )
        assert invite_res.status_code == 200

        client.post("/api/logout")
        _register_and_login(client, "helper", "Secret1234", now_ms)
        invites_res = client.get("/api/repository-invitations")
        assert invites_res.status_code == 200
        invitations = invites_res.json()["invitations"]
        assert any(item["repository_name"] == "alpha_build" for item in invitations)

        accept_res = client.post(
            "/api/repository-invitations/accept",
            json={"owner": "maker", "repository_name": "alpha_build"},
        )
        assert accept_res.status_code == 200

        session_res = client.get("/api/session")
        repositories = session_res.json()["repository_cards"]
        assert any(item["repository_name"] == "alpha_build" for item in repositories)

        edit_res = client.put(
            "/api/repositories/maker/alpha_build/projects/server/file",
            json={"path": "src/app.py", "content": "print('contributor')\n"},
        )
        assert edit_res.status_code == 200

        add_project_res = client.post(
            "/api/repositories/maker/alpha_build/projects",
            json={"name": "client", "description": "Blocked for contributors"},
        )
        assert add_project_res.status_code == 403

        create_res = client.put(
            "/api/repositories/maker/alpha_build/projects/server/file",
            json={"path": "src/new_module.py", "content": "print('blocked')\n"},
        )
        assert create_res.status_code == 403

        upload_res = client.post(
            "/api/repositories/maker/alpha_build/projects/server/upload",
            files=[("files", ("docs/readme.txt", b"nope\n", "text/plain"))],
        )
        assert upload_res.status_code == 403

    def test_upload_files_and_history_store_only_diff(self, client, now_ms, data_root):
        _register_and_login(client, "maker", "Secret1234", now_ms)
        client.post(
            "/api/repositories",
            json={
                "name": "alpha_build",
                "description": "First public test repository",
                "visibility": "public",
                "project_names": ["server"],
                "timestamp": now_ms,
            },
        )

        upload_res = client.post(
            "/api/repositories/maker/alpha_build/projects/server/upload",
            files=[
                ("files", ("src/app.py", b"print('hello')\n", "text/plain")),
                ("files", ("static/site.css", b"body { color: red; }\n", "text/css")),
            ],
        )
        assert upload_res.status_code == 200
        uploaded_paths = [item["path"] for item in upload_res.json()["files"]]
        assert "src/app.py" in uploaded_paths
        assert "static/site.css" in uploaded_paths

        client.put(
            "/api/repositories/maker/alpha_build/projects/server/file",
            json={"path": "src/app.py", "content": "print('bye')\n"},
        )

        history_dir = data_root / "user_projects" / "maker" / "alpha_build" / "history"
        history_files = sorted(history_dir.glob("*.json"))
        assert history_files
        last_entry = history_files[-1].read_text(encoding="utf-8")
        assert "src/app.py" in last_entry
        assert "-print('hello')" in last_entry
        assert "+print('bye')" in last_entry

    def test_upload_rejects_too_many_files(self, client, now_ms, monkeypatch):
        from api import projects as projects_module

        _register_and_login(client, "maker", "Secret1234", now_ms)
        client.post(
            "/api/repositories",
            json={
                "name": "alpha_build",
                "description": "First public test repository",
                "visibility": "public",
                "project_names": ["server"],
                "timestamp": now_ms,
            },
        )
        monkeypatch.setattr(projects_module, "MAX_UPLOAD_FILE_COUNT", 1)

        upload_res = client.post(
            "/api/repositories/maker/alpha_build/projects/server/upload",
            files=[
                ("files", ("src/app.py", b"print('hello')\n", "text/plain")),
                ("files", ("static/site.css", b"body { color: red; }\n", "text/css")),
            ],
        )

        assert upload_res.status_code == 400
        assert "Too many files" in upload_res.json()["detail"]

    def test_upload_rejects_oversized_file(self, client, now_ms, monkeypatch):
        from api import projects as projects_module

        _register_and_login(client, "maker", "Secret1234", now_ms)
        client.post(
            "/api/repositories",
            json={
                "name": "alpha_build",
                "description": "First public test repository",
                "visibility": "public",
                "project_names": ["server"],
                "timestamp": now_ms,
            },
        )
        monkeypatch.setattr(projects_module, "MAX_UPLOAD_FILE_SIZE", 4)

        upload_res = client.post(
            "/api/repositories/maker/alpha_build/projects/server/upload",
            files=[("files", ("src/app.py", b"print('hello')\n", "text/plain"))],
        )

        assert upload_res.status_code == 413
        assert "exceeds" in upload_res.json()["detail"]

    def test_upload_rejects_hidden_path_segments(self, client, now_ms):
        _register_and_login(client, "maker", "Secret1234", now_ms)
        client.post(
            "/api/repositories",
            json={
                "name": "alpha_build",
                "description": "First public test repository",
                "visibility": "public",
                "project_names": ["server"],
                "timestamp": now_ms,
            },
        )

        upload_res = client.post(
            "/api/repositories/maker/alpha_build/projects/server/upload",
            files=[("files", (".env", b"SECRET=1\n", "text/plain"))],
        )

        assert upload_res.status_code == 400
        assert upload_res.json()["detail"] == "Invalid file path"

    def test_repository_quota_blocks_large_write(self, client, now_ms, monkeypatch):
        from utils import repository_content_util

        _register_and_login(client, "maker", "Secret1234", now_ms)
        client.post(
            "/api/repositories",
            json={
                "name": "alpha_build",
                "description": "First public test repository",
                "visibility": "public",
                "project_names": ["server"],
                "timestamp": now_ms,
            },
        )
        monkeypatch.setattr(repository_content_util, "REPOSITORY_STORAGE_QUOTA_BYTES", 8)

        save_res = client.put(
            "/api/repositories/maker/alpha_build/projects/server/file",
            json={
                "path": "src/app.py",
                "content": "print('hello')\n",
            },
        )

        assert save_res.status_code == 400
        assert "quota" in save_res.json()["detail"].lower()

    def test_download_repository_zip(self, client, now_ms):
        _register_and_login(client, "maker", "Secret1234", now_ms)
        client.post(
            "/api/repositories",
            json={
                "name": "alpha_build",
                "description": "First public test repository",
                "visibility": "public",
                "project_names": ["server"],
                "timestamp": now_ms,
            },
        )
        client.put(
            "/api/repositories/maker/alpha_build/projects/server/file",
            json={"path": "src/app.py", "content": "print('zip')\n"},
        )

        res = client.get("/api/repositories/maker/alpha_build/archive.zip")

        assert res.status_code == 200
        assert res.headers["content-type"].startswith("application/zip")
        archive = zipfile.ZipFile(io.BytesIO(res.content))
        assert "alpha_build/server/src/app.py" in archive.namelist()


class TestExploreAndPublicViews:
    def test_repository_viewer_flags_distinguish_owner_from_others(
        self, client, now_ms
    ):
        _register_and_login(client, "maker", "Secret1234", now_ms)
        client.post(
            "/api/repositories",
            json={
                "name": "public_alpha",
                "description": "Visible to everyone",
                "visibility": "public",
                "project_names": ["server"],
                "timestamp": now_ms,
            },
        )

        owner_res = client.get("/api/repositories/maker/public_alpha")
        assert owner_res.status_code == 200
        assert owner_res.json()["viewer_is_owner"] is True
        assert owner_res.json()["viewer_can_edit"] is True

        client.post("/api/logout")
        anonymous_res = client.get("/api/repositories/maker/public_alpha")
        assert anonymous_res.status_code == 200
        assert anonymous_res.json()["viewer_is_owner"] is False
        assert anonymous_res.json()["viewer_can_edit"] is False

        _register_and_login(client, "helper", "Secret1234", now_ms)
        contributor_res = client.get("/api/repositories/maker/public_alpha")
        assert contributor_res.status_code == 200
        assert contributor_res.json()["viewer_is_owner"] is False
        assert contributor_res.json()["viewer_can_edit"] is False

    def test_explore_returns_only_public_repositories(self, client, now_ms, data_root):
        _register_and_login(client, "maker", "Secret1234", now_ms)
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
        _register_and_login(client, "maker", "Secret1234", now_ms)
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
