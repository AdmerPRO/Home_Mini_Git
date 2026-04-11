const form = document.getElementById("loginForm");
const errorMsg = document.getElementById("errorMsg");

async function redirectIfSessionExists() {
    try {
        const res = await fetch("/api/session", {
            method: "GET",
            headers: { "Accept": "application/json" },
            credentials: "same-origin",
        });

        const data = await res.json();
        if (data.authenticated) {
            window.location.replace("/dashboard");
        }
    } catch (err) {
        console.error(err);
    }
}

form.addEventListener("submit", async (e) => {
    e.preventDefault();
    
    const username = form.username.value;
    const password = form.password.value;
    const timestamp = Date.now();

    try {
        const res = await fetch("/api/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password, timestamp })
        });

        const data = await res.json();

        if(res.ok && data.success){
            window.location.href = "/dashboard";
        } else {
            errorMsg.textContent = data.detail || data.message || "Login failed";
        }

    } catch(err){
        errorMsg.textContent = "Error connecting to server";
        console.error(err);
    }
});

redirectIfSessionExists();
