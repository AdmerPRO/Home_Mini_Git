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


class TestMessages:
    def test_send_and_read_message(self, client, now_ms):
        _register_and_login(client, "maker", "Secret1234", now_ms)
        client.post("/api/logout")
        _register_and_login(client, "friend", "Secret1234", now_ms)
        client.post("/api/logout")
        _register_and_login(client, "maker", "Secret1234", now_ms)

        send_res = client.post(
            "/api/messages",
            json={
                "recipient": "friend",
                "subject": "Repo idea",
                "content": "Can you review my Python project?",
            },
        )
        assert send_res.status_code == 200

        client.post("/api/logout")
        _register_and_login(client, "friend", "Secret1234", now_ms)
        inbox_res = client.get("/api/messages")
        assert inbox_res.status_code == 200
        messages = inbox_res.json()["messages"]
        assert len(messages) == 1
        assert messages[0]["sender"] == "maker"
        assert messages[0]["read"] is False

        read_res = client.post(
            "/api/messages/read",
            json={"message_id": messages[0]["id"]},
        )
        assert read_res.status_code == 200

        inbox_res = client.get("/api/messages")
        assert inbox_res.json()["messages"][0]["read"] is True
