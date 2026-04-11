const greeting = document.getElementById("greeting");
const projectsList = document.getElementById("projectsList");
const emptyState = document.getElementById("emptyState");
const logoutButton = document.getElementById("logoutButton");

function renderProjects(projects) {
    projectsList.innerHTML = "";

    if (!Array.isArray(projects) || projects.length === 0) {
        emptyState.hidden = false;
        return;
    }

    emptyState.hidden = true;

    for (const projectName of projects) {
        const item = document.createElement("li");
        item.className = "project-card";
        item.textContent = projectName;
        projectsList.appendChild(item);
    }
}

async function loadSession() {
    const res = await fetch("/api/session", {
        method: "GET",
        headers: { "Accept": "application/json" },
        credentials: "same-origin",
    });

    const data = await res.json();
    if (!data.authenticated) {
        window.location.replace("/login");
        return;
    }

    greeting.textContent = `Hey, ${data.nickname}!`;
    renderProjects(data.projects);
}

logoutButton.addEventListener("click", async () => {
    await fetch("/api/logout", {
        method: "POST",
        credentials: "same-origin",
    });
    window.location.replace("/login");
});

loadSession().catch(() => {
    window.location.replace("/login");
});
