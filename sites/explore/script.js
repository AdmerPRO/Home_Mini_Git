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

function badge(text) {
    const element = document.createElement("span");
    element.className = "badge";
    element.textContent = text;
    return element;
}

function renderRepositories(repositories) {
    const repositoriesGrid = document.getElementById("repositoriesGrid");
    const repositoriesEmpty = document.getElementById("repositoriesEmpty");
    repositoriesGrid.innerHTML = "";

    if (!Array.isArray(repositories) || repositories.length === 0) {
        repositoriesEmpty.hidden = false;
        return;
    }

    repositoriesEmpty.hidden = true;

    for (const repository of repositories) {
        const card = document.createElement("article");
        card.className = "card";

        const title = document.createElement("a");
        title.className = "project-link";
        title.href = `/repositories/${encodeURIComponent(repository.owner)}/${encodeURIComponent(repository.repository_name)}`;
        title.textContent = repository.repository_name;

        const owner = document.createElement("p");
        owner.className = "meta";
        owner.textContent = `by ${repository.owner}`;

        const description = document.createElement("p");
        description.textContent = repository.description;

        const metaRow = document.createElement("div");
        metaRow.className = "meta-row";
        metaRow.appendChild(badge(repository.private ? "Private" : "Public"));
        metaRow.appendChild(badge(`${repository.views} views`));
        metaRow.appendChild(badge(`${repository.projects_count} projects`));
        metaRow.appendChild(badge(`${repository.contributors_count} contributors`));

        const projectNames = document.createElement("p");
        projectNames.className = "meta";
        projectNames.textContent = `Projects: ${repository.project_names.join(", ")}`;

        card.append(title, owner, description, metaRow, projectNames);
        repositoriesGrid.appendChild(card);
    }
}

function renderUsers(users) {
    const usersGrid = document.getElementById("usersGrid");
    const usersEmpty = document.getElementById("usersEmpty");
    usersGrid.innerHTML = "";

    if (!Array.isArray(users) || users.length === 0) {
        usersEmpty.hidden = false;
        return;
    }

    usersEmpty.hidden = true;

    for (const user of users) {
        const card = document.createElement("article");
        card.className = "card";

        const header = document.createElement("div");
        header.className = "card-header";
        header.appendChild(createAvatar(user.display_name || user.username));

        const textWrap = document.createElement("div");
        textWrap.className = "stack";

        const link = document.createElement("a");
        link.className = "user-link";
        link.href = `/users/${encodeURIComponent(user.username)}`;
        link.textContent = user.display_name || user.username;

        const handle = document.createElement("p");
        handle.className = "meta";
        handle.textContent = `@${user.username}`;

        textWrap.append(link, handle);
        header.appendChild(textWrap);

        const bio = document.createElement("p");
        bio.textContent = user.bio;

        const metaRow = document.createElement("div");
        metaRow.className = "meta-row";
        metaRow.appendChild(badge(`${user.public_repository_count} public repositories`));
        metaRow.appendChild(badge(`${user.public_project_total} projects total`));
        metaRow.appendChild(badge(`${user.total_views} total views`));

        card.append(header, bio, metaRow);
        usersGrid.appendChild(card);
    }
}

async function loadExplore() {
    const response = await fetch("/api/explore", {
        headers: { Accept: "application/json" },
        credentials: "same-origin",
    });
    const data = await response.json();
    renderRepositories(data.repositories);
    renderUsers(data.users);
}

loadExplore().catch(() => {
    document.getElementById("repositoriesEmpty").hidden = false;
    document.getElementById("usersEmpty").hidden = false;
});
