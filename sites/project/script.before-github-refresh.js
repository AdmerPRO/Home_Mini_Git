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

const state = {
    owner: "",
    repositoryName: "",
    repository: null,
    viewerIsOwner: false,
    viewerCanEdit: false,
    currentProject: "",
    currentFilePath: "",
};

function setFormAvailability(formId, enabled) {
    const form = document.getElementById(formId);
    form.hidden = !enabled;
    form.setAttribute("aria-hidden", String(!enabled));

    for (const element of form.elements) {
        element.disabled = !enabled;
    }
}

function applyOwnerVisibility() {
    setFormAvailability("addProjectForm", state.viewerIsOwner);
    setFormAvailability("addFileForm", state.viewerIsOwner);
    setFormAvailability("uploadForm", state.viewerIsOwner);
    setFormAvailability("inviteContributorForm", state.viewerIsOwner);
}

function formatBytes(bytes) {
    if (!bytes) {
        return "0 B";
    }
    if (bytes < 1024) {
        return `${bytes} B`;
    }
    if (bytes < 1024 * 1024) {
        return `${(bytes / 1024).toFixed(1)} KB`;
    }
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

async function fetchJson(url, options = {}) {
    const response = await fetch(url, {
        credentials: "same-origin",
        headers: { Accept: "application/json", ...(options.headers || {}) },
        ...options,
    });
    const data = await response.json().catch(() => ({}));
    return { response, data };
}

function renderLanguageStats(stats) {
    const languageStats = document.getElementById("languageStats");
    const languageSummary = document.getElementById("languageSummary");
    languageStats.innerHTML = "";
    languageSummary.textContent = formatBytes(stats.total_bytes || 0);

    for (const item of stats.languages || []) {
        const row = document.createElement("div");
        row.className = "language-row";

        const header = document.createElement("div");
        header.className = "language-head";
        header.append(
            Object.assign(document.createElement("strong"), { textContent: item.language }),
            Object.assign(document.createElement("span"), {
                className: "helper",
                textContent: `${item.percent}%`,
            })
        );

        const track = document.createElement("div");
        track.className = "progress-track";
        const bar = document.createElement("div");
        bar.className = "progress-bar";
        bar.style.width = `${item.percent}%`;
        track.appendChild(bar);

        const footer = document.createElement("div");
        footer.className = "helper";
        footer.textContent = formatBytes(item.bytes);

        row.append(header, track, footer);
        languageStats.appendChild(row);
    }
}

async function loadLanguageStats() {
    const { data } = await fetchJson(
        `/api/repositories/${encodeURIComponent(state.owner)}/${encodeURIComponent(state.repositoryName)}/languages`
    );
    renderLanguageStats(data);
}

function renderProjectTabs(projects) {
    const projectTabs = document.getElementById("projectTabs");
    projectTabs.innerHTML = "";

    for (const project of projects || []) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "tab-button";
        if (project.name === state.currentProject) {
            button.classList.add("tab-button-active");
        }
        button.textContent = project.name;
        button.addEventListener("click", async () => {
            state.currentProject = project.name;
            state.currentFilePath = "";
            renderProjectTabs(state.repository.projects);
            await loadProjectFiles();
        });
        projectTabs.appendChild(button);
    }
}

async function loadProjectFiles() {
    const fileList = document.getElementById("fileList");
    fileList.innerHTML = "";

    if (!state.currentProject) {
        return;
    }

    const { response, data } = await fetchJson(
        `/api/repositories/${encodeURIComponent(state.owner)}/${encodeURIComponent(state.repositoryName)}/projects/${encodeURIComponent(state.currentProject)}/files`
    );
    if (!response.ok) {
        return;
    }

    for (const file of data.files || []) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "file-button";
        if (file.path === state.currentFilePath) {
            button.classList.add("file-button-active");
        }
        button.textContent = file.path;
        button.addEventListener("click", async () => {
            state.currentFilePath = file.path;
            await loadFile(file.path);
            await loadProjectFiles();
        });
        fileList.appendChild(button);
    }

    if (!state.currentFilePath && (data.files || []).length > 0) {
        const readme = data.files.find((file) => file.is_readme) || data.files[0];
        state.currentFilePath = readme.path;
        await loadFile(state.currentFilePath);
        await loadProjectFiles();
    }
}

async function loadFile(path) {
    const fileEditor = document.getElementById("fileEditor");
    const editorTitle = document.getElementById("editorTitle");
    const editorMeta = document.getElementById("editorMeta");
    const saveFileButton = document.getElementById("saveFileButton");

    const query = encodeURIComponent(path);
    const { response, data } = await fetchJson(
        `/api/repositories/${encodeURIComponent(state.owner)}/${encodeURIComponent(state.repositoryName)}/projects/${encodeURIComponent(state.currentProject)}/file?path=${query}`
    );
    if (!response.ok) {
        fileEditor.value = "";
        editorTitle.textContent = "Could not load file";
        editorMeta.textContent = response.status === 404 ? "Missing file" : "Error";
        return;
    }

    fileEditor.value = data.content || "";
    editorTitle.textContent = data.path;
    editorMeta.textContent = `${formatBytes(data.size)} · ${state.currentProject}`;
    fileEditor.readOnly = !state.viewerCanEdit;
    saveFileButton.hidden = !state.viewerCanEdit;
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
    state.owner = owner;
    state.repositoryName = repositoryName;
    state.repository = repository;
    state.viewerIsOwner = Boolean(repositoryData.viewer_is_owner);
    state.viewerCanEdit = Boolean(repositoryData.viewer_can_edit);
    state.currentProject = repository.projects?.[0]?.name || "";
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
    ownerCard.appendChild(
        createAvatar(
            ownerProfile.display_name || ownerProfile.username,
            ownerProfile.avatar_image
        )
    );

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

    document.getElementById("workspaceMode").textContent = state.viewerCanEdit
        ? state.viewerIsOwner
            ? "Owner editor"
            : "Contributor editor"
        : "Read only";
    applyOwnerVisibility();

    renderProjectTabs(repository.projects || []);
    await loadProjectFiles();
    await loadLanguageStats();
}

applyOwnerVisibility();

document.getElementById("saveFileButton").addEventListener("click", async () => {
    const fileEditor = document.getElementById("fileEditor");
    if (!state.viewerCanEdit || !state.currentProject || !state.currentFilePath) {
        return;
    }

    await fetchJson(
        `/api/repositories/${encodeURIComponent(state.owner)}/${encodeURIComponent(state.repositoryName)}/projects/${encodeURIComponent(state.currentProject)}/file`,
        {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                path: state.currentFilePath,
                content: fileEditor.value,
            }),
        }
    );
    await loadLanguageStats();
    await loadProjectFiles();
});

document.getElementById("addFileForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const fileMsg = document.getElementById("fileMsg");
    fileMsg.textContent = "";
    const path = event.currentTarget.elements.path.value.trim();

    const { response, data } = await fetchJson(
        `/api/repositories/${encodeURIComponent(state.owner)}/${encodeURIComponent(state.repositoryName)}/projects/${encodeURIComponent(state.currentProject)}/file`,
        {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ path, content: "" }),
        }
    );
    if (!response.ok) {
        fileMsg.textContent = data.detail || "Could not create the file.";
        return;
    }

    event.currentTarget.reset();
    fileMsg.textContent = "File created.";
    state.currentFilePath = data.file.path;
    await loadProjectFiles();
});

document.getElementById("addProjectForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const projectMsg = document.getElementById("projectMsg");
    projectMsg.textContent = "";

    const payload = {
        name: event.currentTarget.elements.name.value.trim(),
        description: event.currentTarget.elements.description.value.trim(),
    };

    const { response, data } = await fetchJson(
        `/api/repositories/${encodeURIComponent(state.owner)}/${encodeURIComponent(state.repositoryName)}/projects`,
        {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        }
    );
    if (!response.ok) {
        projectMsg.textContent = data.detail || "Could not create the project.";
        return;
    }

    state.repository = data.repository;
    state.currentProject = payload.name;
    event.currentTarget.reset();
    projectMsg.textContent = "Project added.";
    renderProjectTabs(state.repository.projects || []);
    await loadProjectFiles();
});

document.getElementById("uploadForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const uploadMsg = document.getElementById("uploadMsg");
    uploadMsg.textContent = "";

    const formData = new FormData();
    const normalFiles = Array.from(event.currentTarget.elements.upload_files.files || []);
    const folderFiles = Array.from(event.currentTarget.elements.upload_folder.files || []);
    for (const file of [...normalFiles, ...folderFiles]) {
        const relativePath = file.webkitRelativePath || file.name;
        formData.append("files", file, relativePath);
    }

    if (!formData.getAll("files").length) {
        uploadMsg.textContent = "Choose files or a folder first.";
        return;
    }

    const response = await fetch(
        `/api/repositories/${encodeURIComponent(state.owner)}/${encodeURIComponent(state.repositoryName)}/projects/${encodeURIComponent(state.currentProject)}/upload`,
        {
            method: "POST",
            credentials: "same-origin",
            body: formData,
        }
    );
    const data = await response.json();
    if (!response.ok) {
        uploadMsg.textContent = data.detail || "Could not upload files.";
        return;
    }

    event.currentTarget.reset();
    uploadMsg.textContent = `${data.files.length} files uploaded.`;
    await loadLanguageStats();
    await loadProjectFiles();
});

document.getElementById("inviteContributorForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const inviteMsg = document.getElementById("inviteMsg");
    inviteMsg.textContent = "";

    const response = await fetch(
        `/api/repositories/${encodeURIComponent(state.owner)}/${encodeURIComponent(state.repositoryName)}/invite`,
        {
            method: "POST",
            headers: { "Content-Type": "application/json", Accept: "application/json" },
            credentials: "same-origin",
            body: JSON.stringify({
                username: event.currentTarget.elements.username.value.trim(),
            }),
        }
    );
    const data = await response.json();
    if (!response.ok) {
        inviteMsg.textContent = data.detail || "Could not send the invite.";
        return;
    }

    event.currentTarget.reset();
    inviteMsg.textContent = "Invite sent.";
});

loadProject().catch(() => {
    applyOwnerVisibility();
    window.location.replace("/pagenotfound");
});
