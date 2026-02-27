console.log("Scriptoria Script Loaded!");

// --- Auth UI Toggles ---
function showModal() {
    const modal = document.getElementById("modal");
    if (modal) modal.classList.add("visible");
}

function closeModal() {
    const modal = document.getElementById("modal");
    if (modal) modal.classList.remove("visible");
}

function switchAuth(type) {
    const loginForm = document.getElementById("login-form");
    const regForm = document.getElementById("register-form");
    const loginTab = document.getElementById("tab-login");
    const regTab = document.getElementById("tab-register");

    if (!loginForm || !regForm || !loginTab || !regTab) return;

    if (type === 'login') {
        loginForm.classList.remove("hidden");
        regForm.classList.add("hidden");
        loginTab.classList.add("active");
        regTab.classList.remove("active");
    } else {
        loginForm.classList.add("hidden");
        regForm.classList.remove("hidden");
        loginTab.classList.remove("active");
        regTab.classList.add("active");
    }
}

// --- Auth actions ---
async function register(event) {
    const btn = event ? event.currentTarget : null;
    const username = document.getElementById("reg-username")?.value.trim();
    const email = document.getElementById("reg-email")?.value.trim();
    const password = document.getElementById("reg-password")?.value.trim();

    if (!username || !email || !password) return alert("Please fill in all fields.");
    if (password.length < 6) return alert("Password must be at least 6 characters.");

    try {
        if (btn) { btn.disabled = true; btn.innerText = "⏳ CREATING..."; }
        const r = await fetch("/auth/register", {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, email, password })
        });
        const d = await r.json();
        if (r.ok) window.location.href = "/dashboard";
        else alert(d.error || "Registration failed.");
    } catch (e) { alert("Server error."); }
    finally { if (btn) { btn.disabled = false; btn.innerText = "Register"; } }
}

async function login(event) {
    const btn = event ? event.currentTarget : null;
    const email = document.getElementById("login-email")?.value.trim();
    const password = document.getElementById("login-password")?.value.trim();

    if (!email || !password) return alert("Please fill in all fields.");

    try {
        if (btn) { btn.disabled = true; btn.innerText = "⏳ LOGGING IN..."; }
        const r = await fetch("/auth/login", {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, password })
        });
        const d = await r.json();
        if (r.ok) window.location.href = "/dashboard";
        else alert(d.error || "Invalid credentials.");
    } catch (e) { alert("Server error."); }
    finally { if (btn) { btn.disabled = false; btn.innerText = "Login"; } }
}

async function logout() {
    await fetch("/auth/logout", { method: "POST" });
    window.location.href = "/";
}

// --- History SideBar (Optimized) ---

function createHistoryItemElement(item) {
    const div = document.createElement("div");
    div.className = "history-item";
    div.id = `chat-${item.id}`;
    div.onclick = (e) => loadHistoryItem(item, e);

    const date = new Date(item.created_at).toLocaleDateString();
    const displayTitle = item.title || (item.prompt.substring(0, 35) + "...");

    div.innerHTML = `
        <div class="history-item-info">
            <span class="prompt" title="${item.prompt}">${displayTitle}</span>
            <button class="rename-btn" onclick="renameChat('${item.id}', '${displayTitle.replace(/'/g, "\\'")}', event)">✏️</button>
        </div>
        <span class="date">${date}</span>
    `;
    return div;
}

async function fetchHistory() {
    const listEl = document.getElementById("history-list");
    if (!listEl) return;

    try {
        const response = await fetch("/history");
        const data = await response.json();
        listEl.innerHTML = "";

        if (data.history && data.history.length > 0) {
            data.history.forEach(item => {
                listEl.appendChild(createHistoryItemElement(item));
            });
        } else {
            listEl.innerHTML = '<p class="loading-text">No stories yet.</p>';
        }
    } catch (e) {
        listEl.innerHTML = '<p class="loading-text">Failed to load history.</p>';
    }
}

async function renameChat(id, currentTitle, event) {
    event.stopPropagation();
    const newTitle = prompt("Enter new title:", currentTitle);
    if (!newTitle || newTitle.trim() === "" || newTitle === currentTitle) return;

    try {
        const res = await fetch("/rename_chat", {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ id, title: newTitle.trim() })
        });
        if (res.ok) fetchHistory();
    } catch (e) { alert("Rename failed."); }
}

function loadHistoryItem(item, event) {
    const storyField = document.getElementById("story");
    const screenplayField = document.getElementById("screenplay");

    if (storyField) storyField.value = item.prompt;
    if (screenplayField) screenplayField.innerText = item.response;

    document.querySelectorAll(".history-item").forEach(el => el.classList.remove("active"));
    let target = event ? event.target : null;
    while (target && !target.classList.contains('history-item')) target = target.parentElement;
    if (target) target.classList.add("active");
}

function newStory() {
    const storyField = document.getElementById("story");
    const screenplayField = document.getElementById("screenplay");
    if (storyField) storyField.value = "";
    if (screenplayField) screenplayField.innerText = "";
    document.querySelectorAll(".history-item").forEach(el => el.classList.remove("active"));
}

// --- Generation & Metadata Streaming ---

async function generate(event) {
    const storyline = document.getElementById("story")?.value.trim();
    if (!storyline) return alert("Please enter a story idea.");

    const btn = event ? event.currentTarget : null;
    const screenplayEl = document.getElementById("screenplay");
    const historyList = document.getElementById("history-list");

    try {
        if (btn) { btn.disabled = true; btn.innerText = "⏳ GENERATING..."; }
        if (screenplayEl) screenplayEl.innerText = "";

        const response = await fetch("/generate_story", {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ storyline })
        });

        if (!response.ok) throw new Error("Generation failed");

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let fullText = "";

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value);
            const lines = chunk.split("\n");

            for (const line of lines) {
                if (!line.startsWith("data: ")) continue;
                try {
                    const data = JSON.parse(line.slice(6));

                    if (data.text) {
                        fullText += data.text;
                        screenplayEl.innerText = fullText;
                        screenplayEl.scrollTop = screenplayEl.scrollHeight;
                    }
                    // PERFORMANCE WIN: Local sidebar update from meta chunk
                    else if (data.metadata) {
                        console.log("[META] Received new story ID:", data.metadata.id);
                        if (historyList) {
                            // Remove "No stories" text if present
                            if (historyList.querySelector(".loading-text")) historyList.innerHTML = "";
                            // Prepend the new story element immediately
                            const newEl = createHistoryItemElement(data.metadata);
                            historyList.insertBefore(newEl, historyList.firstChild);
                        }
                    }
                } catch (e) { }
            }
        }
    } catch (e) {
        alert(e.message);
    } finally {
        if (btn) { btn.disabled = false; btn.innerText = "GENERATE CONTENT"; }
    }
}

// --- Downloads ---
function download(format) {
    const screenplayText = document.getElementById("screenplay")?.innerText;
    if (!screenplayText) return alert("No content to download.");

    if (format === 'txt') {
        const blob = new Blob([screenplayText], { type: "text/plain" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url; a.download = "screenplay.txt"; a.click();
        return;
    }

    const endpoint = format === 'pdf' ? '/download_pdf' : '/download_docx';
    fetch(endpoint, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ screenplay: screenplayText })
    })
        .then(res => res.blob())
        .then(blob => {
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url; a.download = `screenplay.${format}`; a.click();
        })
        .catch(e => alert("Download failed."));
}

document.addEventListener("DOMContentLoaded", () => {
    if (document.getElementById("history-list")) {
        fetchHistory();
    }
});