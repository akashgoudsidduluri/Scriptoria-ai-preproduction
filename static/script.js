console.log("Scriptoria Script Loaded!");

// --- Auth UI Toggles ---
function showModal() {
    console.log("Showing modal");
    const modal = document.getElementById("modal");
    if (modal) modal.classList.add("visible");
}

function closeModal() {
    console.log("Closing modal");
    const modal = document.getElementById("modal");
    if (modal) modal.classList.remove("visible");
}

function switchAuth(type) {
    console.log("Switching auth to:", type);
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

// --- Auth Backend Actions ---
async function register(event) {
    console.log("Attempting registration...");
    const btn = event ? event.currentTarget : null;

    const username = document.getElementById("reg-username")?.value.trim();
    const email = document.getElementById("reg-email")?.value.trim();
    const password = document.getElementById("reg-password")?.value.trim();

    if (!username || !email || !password) {
        alert("Please fill in all registration fields.");
        return;
    }

    if (password.length < 6) {
        alert("Password must be at least 6 characters.");
        return;
    }

    try {
        if (btn) {
            btn.disabled = true;
            btn.innerText = "Creating Account...";
        }

        const response = await fetch("/auth/register", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, email, password })
        });

        const data = await response.json();
        console.log("Registration response:", data);

        if (response.ok && data.success) {
            alert("Registration successful! Welcome to Scriptoria.");
            window.location.href = "/dashboard";
        } else {
            alert(data.error || "Registration failed. Try again.");
        }
    } catch (e) {
        console.error("Register Error:", e);
        alert("Error connecting to server. Please check your connection.");
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerText = "Register";
        }
    }
}

async function login(event) {
    console.log("Attempting login...");
    const btn = event ? event.currentTarget : null;

    const email = document.getElementById("login-email")?.value.trim();
    const password = document.getElementById("login-password")?.value.trim();

    if (!email || !password) {
        alert("Please fill in both email and password.");
        return;
    }

    try {
        if (btn) {
            btn.disabled = true;
            btn.innerText = "Logging in...";
        }

        const response = await fetch("/auth/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, password })
        });
        const data = await response.json();
        console.log("Login response:", data);

        if (response.ok && data.success) {
            window.location.href = "/dashboard";
        } else {
            alert(data.error || "Login failed. Check your email/password.");
        }
    } catch (e) {
        console.error("Login Error:", e);
        alert("Error connecting to server.");
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerText = "Login";
        }
    }
}

async function logout() {
    console.log("Logging out...");
    try {
        const response = await fetch("/auth/logout", {
            method: "POST",
            headers: { "Content-Type": "application/json" }
        });
        if (response.ok) {
            window.location.href = "/";
        } else {
            console.error("Logout failed on server");
            window.location.href = "/";
        }
    } catch (e) {
        console.error("Logout error:", e);
        window.location.href = "/";
    }
}

// --- History & Dashboard Actions ---
async function fetchHistory() {
    console.log("Fetching history...");
    const listEl = document.getElementById("history-list");
    if (!listEl) return;

    try {
        const response = await fetch("/history");
        const data = await response.json();

        if (data.history && data.history.length > 0) {
            listEl.innerHTML = "";
            data.history.forEach(item => {
                const div = document.createElement("div");
                div.className = "history-item";
                div.onclick = (e) => loadHistoryItem(item, e);

                const date = new Date(item.created_at).toLocaleDateString();
                const displayTitle = item.title || (item.prompt.substring(0, 35) + (item.prompt.length > 35 ? "..." : ""));

                div.innerHTML = `
                    <div class="history-item-info">
                        <span class="prompt" title="${item.prompt}">${displayTitle}</span>
                        <button class="rename-btn" onclick="renameChat('${item.id}', '${displayTitle.replace(/'/g, "\\'")}', event)">✏️</button>
                    </div>
                    <span class="date">${date}</span>
                `;
                listEl.appendChild(div);
            });
        } else {
            listEl.innerHTML = '<p class="loading-text">No stories yet.</p>';
        }
    } catch (e) {
        console.error("Error fetching history:", e);
        listEl.innerHTML = '<p class="loading-text">Failed to load history.</p>';
    }
}

async function renameChat(id, currentTitle, event) {
    event.stopPropagation(); // Don't trigger loadHistoryItem
    const newTitle = prompt("Enter new title for this story:", currentTitle);

    if (!newTitle || newTitle.trim() === "" || newTitle === currentTitle) {
        return;
    }

    try {
        const response = await fetch("/rename_chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ id, title: newTitle.trim() })
        });
        const data = await response.json();

        if (response.ok && data.success) {
            fetchHistory(); // Refresh list 
        } else {
            alert(data.error || "Failed to rename story.");
        }
    } catch (e) {
        console.error("Rename error:", e);
        alert("Server error while renaming.");
    }
}

function loadHistoryItem(item, event) {
    console.log("Loading history item:", item.id);
    const storyField = document.getElementById("story");
    const screenplayField = document.getElementById("screenplay");

    if (storyField) storyField.value = item.prompt;
    if (screenplayField) screenplayField.innerText = item.response;

    // Highlight active item
    document.querySelectorAll(".history-item").forEach(el => el.classList.remove("active"));

    let target = event ? event.target : null;
    while (target && !target.classList.contains('history-item')) {
        target = target.parentElement;
    }
    if (target) target.classList.add("active");
}

function newStory() {
    console.log("Clearing for new story");
    const storyField = document.getElementById("story");
    const screenplayField = document.getElementById("screenplay");

    if (storyField) storyField.value = "";
    if (screenplayField) screenplayField.innerText = "";
    document.querySelectorAll(".history-item").forEach(el => el.classList.remove("active"));
}

// --- Generation & Streaming ---
async function generate(event) {
    const storyline = document.getElementById("story")?.value.trim();
    if (!storyline) {
        alert("Please enter a story idea.");
        return;
    }

    const btn = event ? event.currentTarget : null;
    const screenplayEl = document.getElementById("screenplay");

    try {
        if (btn) {
            btn.disabled = true;
            btn.innerText = "⏳ GENERATING...";
        }

        if (screenplayEl) screenplayEl.innerText = "";

        console.log("Starting generation stream...");
        const response = await fetch("/generate_story", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ storyline })
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.error || "Generation failed");
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let fullText = "";

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value);
            const lines = chunk.split("\n");

            for (const line of lines) {
                if (line.startsWith("data: ")) {
                    try {
                        const data = JSON.parse(line.slice(6));
                        if (data.text) {
                            fullText += data.text;
                            if (screenplayEl) {
                                screenplayEl.innerText = fullText;
                                screenplayEl.scrollTop = screenplayEl.scrollHeight;
                            }
                        }
                    } catch (e) {
                        console.warn("SSE Parse Error", e);
                    }
                }
            }
        }

        console.log("Generation complete.");

    } catch (e) {
        console.error("Generate Error:", e);
        alert(e.message);
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerText = "Generate Content";
        }
        // Force a slight delay to ensure DB persistence completes
        setTimeout(fetchHistory, 1000);
    }
}

// --- Downloads ---
function download(format) {
    console.log("Downloading in format:", format);
    const screenplayEl = document.getElementById("screenplay");
    const screenplayText = screenplayEl ? screenplayEl.innerText : "";

    if (!screenplayText) {
        alert("No content to download.");
        return;
    }

    if (format === 'txt') {
        const blob = new Blob([screenplayText], { type: "text/plain" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "screenplay.txt";
        a.click();
        return;
    }

    const endpoint = format === 'pdf' ? '/download_pdf' : '/download_docx';

    fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ screenplay: screenplayText })
    })
        .then(res => res.blob())
        .then(blob => {
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `screenplay.${format}`;
            a.click();
        })
        .catch(e => {
            console.error("Download Error:", e);
            alert("Failed to generate download on server.");
        });
}

// --- Init ---
document.addEventListener("DOMContentLoaded", () => {
    console.log("DOM Content Loaded");
    if (document.getElementById("history-list")) {
        fetchHistory();
    }
});