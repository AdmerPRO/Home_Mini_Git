const form = document.getElementById("loginForm");
const errorMsg = document.getElementById("errorMsg");

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

        if(data.success){
            window.location.href = "/dashboard";
        } else {
            errorMsg.textContent = data.message || "Login failed";
        }

    } catch(err){
        errorMsg.textContent = "Error connecting to server";
        console.error(err);
    }
});