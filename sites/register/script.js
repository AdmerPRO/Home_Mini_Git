const form = document.getElementById("registerForm");
const errorMsg = document.getElementById("errorMsg");

form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const username = form.username.value.trim();
    const password = form.password.value;
    if (username.length < 3) {
        errorMsg.textContent = "Username must have at least 3 characters";
        return;
    }

    if (password.length < 6) {
        errorMsg.textContent = "Password must have at least 6 characters";
        return;
    }

    try {
        const res = await fetch("/api/register", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password })
        });

        const data = await res.json();

        if (res.ok && data.success) {
            window.location.href = "/dashboard";
        } else {
            if (Array.isArray(data.detail)) {
                errorMsg.textContent = data.detail.map((item) => item.msg).join(", ");
            } else {
                errorMsg.textContent = data.detail || data.message || "Registration failed";
            }
        }

    } catch (err) {
        errorMsg.textContent = "Error connecting to server";
        console.error(err);
    }
});
