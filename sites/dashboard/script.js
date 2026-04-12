const greeting = document.getElementById("greeting");
const profileLead = document.getElementById("profileLead");
const repositoriesList = document.getElementById("repositoriesList");
const emptyState = document.getElementById("emptyState");
const logoutButton = document.getElementById("logoutButton");
const repositoryCount = document.getElementById("repositoryCount");
const createRepositoryForm = document.getElementById("createRepositoryForm");
const createRepositoryMsg = document.getElementById("createRepositoryMsg");
const profileForm = document.getElementById("profileForm");
const profileMsg = document.getElementById("profileMsg");
const profilePreview = document.getElementById("profilePreview");

function avatarColor(seed) {
    let hash = 0;
    for (const char of seed) {
        hash = ((hash << 5) - hash + char.charCodeAt(0)) | 0;
    }
    const hue = Math.abs(hash) % 360;
    return `hsl(${hue}, 55%, 42%)`;
}

function initials(label) {
    return label
        .split(/[\s_-]+/)
        .filter(Boolean)
        .slice(0, 2)
        .map((part) => part[0]?.toUpperCase() ?? "")
        .join("") || "?";
}

function createAvatar(label) {
    const avatar = document.createElement("div");
    avatar.className = "avatar";
    avatar.style.background = avatarColor(label);
    avatar.textContent = initials(label);
    return avatar;
}

function pill(text) {
    const element = document.createElement("span");
    element.className = "pill";
    element.textContent = text;
    return element;
}

function repositoryProjects(projectNames) {
    const meta = document.createElement("div");
    meta.className = "meta-row";
    for (const name of projectNames || []) {
        meta.appendChild(pill(name));
    }
    return meta;
}

function renderRepositories(repositories) {
    repositoriesList.innerHTML = "";
    repositoryCount.textContent = `${Array.isArray(repositories) ? repositories.length : 0} repositories`;

    if (!Array.isArray(repositories) || repositories.length === 0) {
        emptyState.hidden = false;
        return;
    }

    emptyState.hidden = true;

    for (const repository of repositories) {
        const item = document.createElement("li");
        item.className = "project-card";

        const link = document.createElement("a");
        link.className = "project-link";
        link.href = `/repositories/${encodeURIComponent(repository.owner)}/${encodeURIComponent(repository.repository_name)}`;
        link.textContent = repository.repository_name;

        const description = document.createElement("p");
        description.textContent = repository.description;

        const meta = document.createElement("div");
        meta.className = "meta-row";
        meta.appendChild(pill(repository.private ? "Private" : "Public"));
        meta.appendChild(pill(`${repository.views} views`));
        meta.appendChild(pill(`${repository.projects_count} projects`));
        meta.appendChild(pill(`${repository.contributors_count} contributors`));

        item.append(link, description, meta, repositoryProjects(repository.project_names));
        repositoriesList.appendChild(item);
    }
}

function renderProfile(profile, username) {
    if (!profile) {
        return;
    }

    profileLead.textContent = profile.bio;
    profilePreview.innerHTML = "";

    const header = document.createElement("div");
    header.className = "profile-header";
    header.appendChild(createAvatar(profile.display_name || username));

    const textWrap = document.createElement("div");
    const name = document.createElement("h2");
    name.textContent = profile.display_name || username;
    const handle = document.createElement("p");
    handle.className = "status-message";
    handle.textContent = `@${username}`;
    textWrap.append(name, handle);
    header.appendChild(textWrap);

    const bio = document.createElement("p");
    bio.textContent = profile.bio;

    const meta = document.createElement("div");
    meta.className = "meta-row";
    meta.appendChild(pill(`${profile.public_repository_count} public repositories`));
    meta.appendChild(pill(`${profile.public_project_total} total projects`));
    meta.appendChild(pill(`${profile.total_views} total views`));

    profilePreview.append(header, bio, meta);
    profileForm.display_name.value = profile.display_name || username;
    profileForm.bio.value = profile.bio || "";
}

async function loadSession() {
    const res = await fetch("/api/session", {
        method: "GET",
        headers: { Accept: "application/json" },
        credentials: "same-origin",
    });

    const data = await res.json();
    if (!data.authenticated) {
        window.location.replace("/login");
        return;
    }

    const displayName = data.profile?.display_name || data.nickname;
    greeting.textContent = `Hey, ${displayName}!`;
    renderRepositories(data.repository_cards || []);
    renderProfile(data.profile, data.nickname);
}

logoutButton.addEventListener("click", async () => {
    await fetch("/api/logout", {
        method: "POST",
        credentials: "same-origin",
    });
    window.location.replace("/login");
});

createRepositoryForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    createRepositoryMsg.textContent = "";

    const projectNames = createRepositoryForm.project_names.value
        .split(/[\n,]+/)
        .map((item) => item.trim())
        .filter(Boolean);

    const payload = {
        name: createRepositoryForm.name.value.trim(),
        description: createRepositoryForm.description.value.trim(),
        visibility: createRepositoryForm.visibility.value,
        project_names: projectNames,
        timestamp: Date.now(),
    };

    const response = await fetch("/api/repositories", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        credentials: "same-origin",
        body: JSON.stringify(payload),
    });

    const data = await response.json();
    if (!response.ok) {
        createRepositoryMsg.textContent = data.detail || "Could not create repository.";
        return;
    }

    createRepositoryForm.reset();
    createRepositoryMsg.textContent = "Repository created.";
    await loadSession();
});

profileForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    profileMsg.textContent = "";

    const payload = {
        display_name: profileForm.display_name.value.trim(),
        bio: profileForm.bio.value.trim(),
    };

    const response = await fetch("/api/profile", {
        method: "PATCH",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        credentials: "same-origin",
        body: JSON.stringify(payload),
    });

    const data = await response.json();
    if (!response.ok) {
        profileMsg.textContent = data.detail || "Could not update profile.";
        return;
    }

    profileMsg.textContent = "Profile updated.";
    await loadSession();
});

loadSession().catch(() => {
    window.location.replace("/login");
});
