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
const messageForm = document.getElementById("messageForm");
const messageMsg = document.getElementById("messageMsg");
const messagesList = document.getElementById("messagesList");
const messagesEmpty = document.getElementById("messagesEmpty");
const messageCount = document.getElementById("messageCount");
const invitesList = document.getElementById("invitesList");
const invitesEmpty = document.getElementById("invitesEmpty");
const inviteCount = document.getElementById("inviteCount");
let currentProfile = null;

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

    currentProfile = profile;
    profileLead.textContent = profile.bio;
    profilePreview.innerHTML = "";

    const header = document.createElement("div");
    header.className = "profile-header";
    header.appendChild(createAvatar(profile.display_name || username, profile.avatar_image));

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
    profileForm.elements.display_name.value = profile.display_name || username;
    profileForm.elements.bio.value = profile.bio || "";
    profileForm.elements.avatar_file.value = "";
}

function formatDate(timestamp) {
    return new Date(timestamp).toLocaleString("pl-PL", {
        dateStyle: "medium",
        timeStyle: "short",
    });
}

async function markMessageRead(messageId) {
    await fetch("/api/messages/read", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        credentials: "same-origin",
        body: JSON.stringify({ message_id: messageId }),
    });
}

function renderMessages(messages) {
    messagesList.innerHTML = "";
    messageCount.textContent = `${Array.isArray(messages) ? messages.length : 0} messages`;

    if (!Array.isArray(messages) || messages.length === 0) {
        messagesEmpty.hidden = false;
        return;
    }

    messagesEmpty.hidden = true;

    for (const message of messages) {
        const card = document.createElement("article");
        card.className = "mail-card";
        if (!message.read) {
            card.classList.add("mail-card-unread");
        }

        const title = document.createElement("div");
        title.className = "mail-head";

        const subject = document.createElement("strong");
        subject.textContent = message.subject || "No subject";

        const from = document.createElement("span");
        from.className = "helper";
        from.textContent = `from @${message.sender}`;

        title.append(subject, from);

        const body = document.createElement("p");
        body.textContent = message.content;

        const footer = document.createElement("div");
        footer.className = "meta-row";
        footer.appendChild(pill(formatDate(message.created_at)));
        if (!message.read) {
            const unread = document.createElement("button");
            unread.type = "button";
            unread.className = "btn ghost btn-small";
            unread.textContent = "Mark as read";
            unread.addEventListener("click", async () => {
                await markMessageRead(message.id);
                await loadMessages();
            });
            footer.appendChild(unread);
        }

        card.append(title, body, footer);
        messagesList.appendChild(card);
    }
}

async function loadMessages() {
    const response = await fetch("/api/messages", {
        method: "GET",
        headers: { Accept: "application/json" },
        credentials: "same-origin",
    });

    if (!response.ok) {
        renderMessages([]);
        return;
    }

    const data = await response.json();
    renderMessages(data.messages || []);
}

async function acceptInvite(owner, repositoryName) {
    await fetch("/api/repository-invitations/accept", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        credentials: "same-origin",
        body: JSON.stringify({ owner, repository_name: repositoryName }),
    });
}

function renderInvites(invitations) {
    invitesList.innerHTML = "";
    inviteCount.textContent = `${Array.isArray(invitations) ? invitations.length : 0} invites`;

    if (!Array.isArray(invitations) || invitations.length === 0) {
        invitesEmpty.hidden = false;
        return;
    }

    invitesEmpty.hidden = true;

    for (const invitation of invitations) {
        const card = document.createElement("article");
        card.className = "mail-card mail-card-unread";

        const title = document.createElement("div");
        title.className = "mail-head";

        const subject = document.createElement("strong");
        subject.textContent = `${invitation.owner}/${invitation.repository_name}`;

        const from = document.createElement("span");
        from.className = "helper";
        from.textContent = "Contributor invitation";
        title.append(subject, from);

        const body = document.createElement("p");
        body.textContent = invitation.description;

        const footer = document.createElement("div");
        footer.className = "meta-row";
        footer.appendChild(pill(formatDate(invitation.created_at)));

        const acceptButton = document.createElement("button");
        acceptButton.type = "button";
        acceptButton.className = "btn ghost btn-small";
        acceptButton.textContent = "Accept";
        acceptButton.addEventListener("click", async () => {
            await acceptInvite(invitation.owner, invitation.repository_name);
            await loadInvites();
            await loadSession();
        });
        footer.appendChild(acceptButton);

        card.append(title, body, footer);
        invitesList.appendChild(card);
    }
}

async function loadInvites() {
    const response = await fetch("/api/repository-invitations", {
        method: "GET",
        headers: { Accept: "application/json" },
        credentials: "same-origin",
    });

    if (!response.ok) {
        renderInvites([]);
        return;
    }

    const data = await response.json();
    renderInvites(data.invitations || []);
}

function readAvatarFile(file) {
    return new Promise((resolve, reject) => {
        if (!file) {
            resolve(currentProfile?.avatar_image || "");
            return;
        }

        const reader = new FileReader();
        reader.onload = () => resolve(String(reader.result || ""));
        reader.onerror = () => reject(new Error("Could not read image"));
        reader.readAsDataURL(file);
    });
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
    await loadMessages();
    await loadInvites();
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

    const projectNames = createRepositoryForm.elements.project_names.value
        ? createRepositoryForm.elements.project_names.value
            .split(/[\n,]+/)
            .map((item) => item.trim())
            .filter(Boolean)
        : [];

    const payload = {
        name: createRepositoryForm.elements.name.value.trim(),
        description: createRepositoryForm.elements.description.value.trim(),
        visibility: createRepositoryForm.elements.visibility.value,
        project_names: projectNames,
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

    let avatarImage = currentProfile?.avatar_image || "";
    try {
        avatarImage = await readAvatarFile(profileForm.elements.avatar_file.files[0]);
    } catch (error) {
        profileMsg.textContent = "Could not read the selected image.";
        return;
    }

    const payload = {
        display_name: profileForm.elements.display_name.value.trim(),
        bio: profileForm.elements.bio.value.trim(),
        avatar_image: avatarImage,
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

messageForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    messageMsg.textContent = "";

    const payload = {
        recipient: messageForm.elements.recipient.value.trim(),
        subject: messageForm.elements.subject.value.trim(),
        content: messageForm.elements.content.value.trim(),
    };

    const response = await fetch("/api/messages", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        credentials: "same-origin",
        body: JSON.stringify(payload),
    });

    const data = await response.json();
    if (!response.ok) {
        messageMsg.textContent = data.detail || "Could not send the message.";
        return;
    }

    messageForm.reset();
    messageMsg.textContent = "Message sent.";
    await loadMessages();
});

loadSession().catch(() => {
    window.location.replace("/login");
});
