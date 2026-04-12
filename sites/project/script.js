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

async function loadProject() {
    const [, , ownerSegment, repositorySegment] = window.location.pathname.split("/");
    const owner = decodeURIComponent(ownerSegment || "");
    const repositoryName = decodeURIComponent(repositorySegment || "");

    const repositoryResponse = await fetch(
        `/api/repositories/${encodeURIComponent(owner)}/${encodeURIComponent(repositoryName)}`,
        {
            headers: { Accept: "application/json" },
            credentials: "same-origin",
        }
    );

    if (!repositoryResponse.ok) {
        window.location.replace("/pagenotfound");
        return;
    }

    const repositoryData = await repositoryResponse.json();
    const userResponse = await fetch(`/api/users/${encodeURIComponent(owner)}`, {
        headers: { Accept: "application/json" },
        credentials: "same-origin",
    });

    if (!userResponse.ok) {
        window.location.replace("/pagenotfound");
        return;
    }

    const repository = repositoryData.repository;
    const ownerProfile = (await userResponse.json()).profile;

    document.getElementById("repositoryTitle").textContent = repository.repository_name;
    document.getElementById("repositoryDescription").textContent = repository.description;

    const repositoryMeta = document.getElementById("repositoryMeta");
    repositoryMeta.innerHTML = "";
    repositoryMeta.appendChild(badge(repository.private ? "Private" : "Public"));
    repositoryMeta.appendChild(badge(`${repository.views} views`));
    repositoryMeta.appendChild(badge(`${repository.projects_count} projects`));
    repositoryMeta.appendChild(badge(`${repository.contributors_count} contributors`));

    const repositoryProjects = document.getElementById("repositoryProjects");
    repositoryProjects.innerHTML = "";
    for (const project of repository.projects) {
        const item = document.createElement("div");
        item.className = "owner-text";

        const title = document.createElement("strong");
        title.textContent = project.name;

        const description = document.createElement("p");
        description.textContent = project.description;

        item.append(title, description);
        repositoryProjects.appendChild(item);
    }

    const ownerProfileLink = document.getElementById("ownerProfileLink");
    ownerProfileLink.href = `/users/${encodeURIComponent(ownerProfile.username)}`;

    const ownerCard = document.getElementById("ownerCard");
    ownerCard.innerHTML = "";
    ownerCard.appendChild(createAvatar(ownerProfile.display_name || ownerProfile.username));

    const text = document.createElement("div");
    text.className = "owner-text";

    const ownerLink = document.createElement("a");
    ownerLink.className = "owner-link";
    ownerLink.href = `/users/${encodeURIComponent(ownerProfile.username)}`;
    ownerLink.textContent = ownerProfile.display_name || ownerProfile.username;

    const handle = document.createElement("p");
    handle.textContent = `@${ownerProfile.username}`;

    const bio = document.createElement("p");
    bio.textContent = ownerProfile.bio;

    text.append(ownerLink, handle, bio);
    ownerCard.appendChild(text);
}

loadProject().catch(() => {
    window.location.replace("/pagenotfound");
});
