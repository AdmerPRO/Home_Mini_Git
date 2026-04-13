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

function createAvatar(label, avatarImage = "") {
    if (avatarImage) {
        const image = document.createElement("img");
        image.className = "avatar avatar-image";
        image.src = avatarImage;
        image.alt = label;
        return image;
    }
    const avatar = document.createElement("div");
    avatar.className = "avatar";
    avatar.style.background = avatarColor(label);
    avatar.textContent = initials(label);
    return avatar;
}

function badge(text) {
    const element = document.createElement("span");
    element.className = "badge";
    element.textContent = text;
    return element;
}

function renderProfile(profile) {
    const profileHeader = document.getElementById("profileHeader");
    const profileBio = document.getElementById("profileBio");
    const profileMeta = document.getElementById("profileMeta");
    profileHeader.innerHTML = "";
    profileMeta.innerHTML = "";

    const avatar = createAvatar(
        profile.display_name || profile.username,
        profile.avatar_image
    );
    const identity = document.createElement("div");
    identity.className = "identity";

    const name = document.createElement("h1");
    name.textContent = profile.display_name || profile.username;

    const handle = document.createElement("p");
    handle.className = "handle";
    handle.textContent = `@${profile.username}`;

    identity.append(name, handle);
    profileHeader.append(avatar, identity);
    profileBio.textContent = profile.bio;

    profileMeta.appendChild(badge(`${profile.public_repository_count} public repositories`));
    profileMeta.appendChild(badge(`${profile.public_project_total} projects total`));
    profileMeta.appendChild(badge(`${profile.total_views} total views`));
}

function renderRepositories(repositories) {
    const repositoriesGrid = document.getElementById("repositoriesGrid");
    const emptyState = document.getElementById("emptyState");
    repositoriesGrid.innerHTML = "";

    if (!Array.isArray(repositories) || repositories.length === 0) {
        emptyState.hidden = false;
        return;
    }

    emptyState.hidden = true;

    for (const repository of repositories) {
        const card = document.createElement("article");
        card.className = "card";

        const link = document.createElement("a");
        link.className = "project-link";
        link.href = `/repositories/${encodeURIComponent(repository.owner)}/${encodeURIComponent(repository.repository_name)}`;
        link.textContent = repository.repository_name;

        const description = document.createElement("p");
        description.textContent = repository.description;

        const meta = document.createElement("div");
        meta.className = "meta-row";
        meta.appendChild(badge(`${repository.views} views`));
        meta.appendChild(badge(`${repository.projects_count} projects`));
        meta.appendChild(badge(`${repository.contributors_count} contributors`));

        const projectsLead = document.createElement("p");
        projectsLead.className = "handle";
        projectsLead.textContent = `Projects: ${repository.project_names.join(", ")}`;

        card.append(link, description, meta, projectsLead);
        repositoriesGrid.appendChild(card);
    }
}

async function loadProfile() {
    const username = decodeURIComponent(window.location.pathname.split("/")[2] || "");
    const response = await fetch(`/api/users/${encodeURIComponent(username)}`, {
        headers: { Accept: "application/json" },
        credentials: "same-origin",
    });

    if (!response.ok) {
        window.location.replace("/pagenotfound");
        return;
    }

    const data = await response.json();
    renderProfile(data.profile);
    renderRepositories(data.repositories);
}

loadProfile().catch(() => {
    window.location.replace("/pagenotfound");
});
