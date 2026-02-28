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

// --- Character Bible UI ---
let selectedCharacterIds = new Set();
let allCharacters = []; // Global cache for downloads

function showCharacterForm() {
    const modal = document.getElementById("char-modal");
    if (modal) modal.style.display = "block";
}

function closeCharModal() {
    const modal = document.getElementById("char-modal");
    if (modal) modal.style.display = "none";
}

// --- Navigation & Tabs ---
function switchTab(tabId) {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

    // Support either 'profiles' or 'settings'
    const btn = document.querySelector(`.tab-btn[onclick*="${tabId}"]`);
    if (btn) btn.classList.add('active');

    const content = document.getElementById(`${tabId}-section`);
    if (content) content.classList.add('active');
}

function switchResultTab(tab) {
    const screenplayTab = document.querySelector(".tab:nth-child(1)");
    const profileTab = document.querySelector(".tab:nth-child(2)");
    const screenplayCont = document.getElementById("screenplay-container");
    const profileCont = document.getElementById("profile-container");

    if (tab === "screenplay") {
        screenplayTab.classList.add("active");
        profileTab.classList.remove("active");
        screenplayCont.classList.remove("hidden");
        profileCont.classList.add("hidden");
    } else {
        profileTab.classList.add("active");
        screenplayTab.classList.remove("active");
        profileCont.classList.remove("hidden");
        screenplayCont.classList.add("hidden");
    }
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
    const storyField = document.getElementById("story-input");
    const screenplayField = document.getElementById("screenplay");

    if (storyField) storyField.value = item.prompt;
    if (screenplayField) screenplayField.innerText = item.response;

    // Restore Cinematic Settings
    document.getElementById('story-location').value = item.location_context || "";
    document.getElementById('story-bgm').value = item.bgm_preference || "";

    // Restore Selected Characters
    selectedCharacterIds.clear();
    if (item.active_character_ids) {
        try {
            const ids = JSON.parse(item.active_character_ids);
            ids.forEach(id => selectedCharacterIds.add(id));
        } catch (e) { console.error("Could not parse character IDs", e); }
    }

    // Ensure allCharacters is loaded before rendering
    if (allCharacters.length === 0) {
        fetchCharacters().then(() => renderCharacters());
    } else {
        renderCharacters();
    }

    document.querySelectorAll(".history-item").forEach(el => el.classList.remove("active"));
    let target = event ? event.target : null;
    while (target && !target.classList.contains('history-item')) target = target.parentElement;
    if (target) target.classList.add("active");
}

function newStory() {
    document.getElementById('screenplay').innerHTML = '<p class="placeholder-text">Cinematic results will appear here...</p>';
    document.getElementById('story-input').value = "";
    document.getElementById('story-location').value = "";
    document.getElementById('story-bgm').value = "";
    selectedCharacterIds.clear();
    renderCharacters();
    document.querySelectorAll(".history-item").forEach(el => el.classList.remove("active"));
}

// --- Character Bible Actions ---

function renderCharacters() {
    const listEl = document.getElementById("character-list");
    const gridEl = document.getElementById("character-grid");
    if (!listEl || !gridEl) return;

    listEl.innerHTML = "";
    gridEl.innerHTML = "";

    const activeChars = allCharacters.filter(c => selectedCharacterIds.has(c.id));

    // 1. Sidebar list (Show ALL characters, with selection state)
    if (allCharacters && allCharacters.length > 0) {
        allCharacters.forEach(char => {
            const isSelected = selectedCharacterIds.has(char.id);
            const item = document.createElement("div");
            item.className = `char-item ${isSelected ? 'active' : ''}`;
            item.innerHTML = `
                <div style="display:flex; align-items:center; gap:8px;">
                    <input type="checkbox" ${isSelected ? 'checked' : ''} style="pointer-events:none;">
                    <span>${char.name}</span>
                </div>
                <button onclick="deleteCharacter('${char.id}', event)" style="background:none;border:none;cursor:pointer;opacity:0.5;">×</button>
            `;
            item.onclick = () => toggleCharacterSelection(char);
            listEl.appendChild(item);
        });
    } else {
        listEl.innerHTML = '<p class="loading-text">No characters yet.</p>';
    }

    // 2. Profile Grid Card (ONLY show selected characters for the active story)
    if (activeChars.length > 0) {
        activeChars.forEach(char => {
            const card = document.createElement("div");
            card.className = "char-card glass";
            card.innerHTML = `
                <h4>${char.name}</h4>
                <p>${char.description}</p>
                ${char.personality ? `<p class="meta">Personality: ${char.personality}</p>` : ''}
            `;
            gridEl.appendChild(card);
        });
    } else {
        gridEl.innerHTML = `
            <div style="text-align:center; color:rgba(255,255,255,0.3); padding:40px;">
                <p>No characters selected for this story.</p>
                <p style="font-size:0.8rem; margin-top:10px;">Select profiles from the sidebar to include them in your script.</p>
            </div>`;
    }

    updateActiveCharBar(allCharacters);
}

async function autoGenerateCinematic(type) {
    const storyline = document.getElementById("story-input").value.trim();
    if (!storyline) return alert("Please enter a story idea first.");

    const btn = document.querySelector(`.magic-btn-tiny[onclick*="${type}"]`);
    const input = document.getElementById(type === 'location' ? 'story-location' : 'story-bgm');

    try {
        if (btn) { btn.disabled = true; btn.innerText = "⏳"; }
        const res = await fetch("/generate_cinematic_setting", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ storyline, type })
        });
        const data = await res.json();
        if (res.ok) {
            input.value = data.suggestion;
        } else {
            alert(data.error || "AI Magic failed.");
        }
    } catch (e) {
        alert("Server error.");
    } finally {
        if (btn) { btn.disabled = false; btn.innerText = "✨"; }
    }
}

async function fetchCharacters() {
    try {
        const res = await fetch("/get_characters");
        const data = await res.json();
        allCharacters = data.characters || [];
        renderCharacters();
    } catch (e) {
        console.error("Failed to fetch characters", e);
    }
}

async function autoGenerateCharacter() {
    const nameInput = document.getElementById("char-name");
    const descInput = document.getElementById("char-desc");
    const persInput = document.getElementById("char-personality");
    const saveBtn = document.getElementById("save-char-btn");

    const storyInput = document.getElementById("story-input").value.trim();

    try {
        if (saveBtn) { saveBtn.disabled = true; saveBtn.innerText = "✨ MAGIC IN PROGRESS..."; }
        const res = await fetch("/generate_character", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                name: nameInput.value.trim(),
                storyline: storyInput
            })
        });
        const data = await res.json();
        if (res.ok) {
            nameInput.value = data.name;
            descInput.value = data.description;
            persInput.value = data.personality;
        } else {
            alert("AI Magic failed: " + (data.error || "Unknown error"));
        }
    } catch (e) {
        alert("Server error during generation.");
    } finally {
        if (saveBtn) { saveBtn.disabled = false; saveBtn.innerText = "Save Profile"; }
    }
}

async function saveCharacter() {
    const name = document.getElementById("char-name").value.trim();
    const description = document.getElementById("char-desc").value.trim();
    const personality = document.getElementById("char-personality").value.trim();

    if (!name || !description) return alert("Name and description are required.");

    try {
        const res = await fetch("/save_character", {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name, description, personality })
        });
        if (res.ok) {
            closeCharModal();
            fetchCharacters();
            // Clear form
            document.getElementById("char-name").value = "";
            document.getElementById("char-desc").value = "";
            document.getElementById("char-personality").value = "";
        } else {
            const d = await res.json();
            alert(d.error || "Failed to save.");
        }
    } catch (e) { alert("Server error."); }
}

async function deleteCharacter(id, event) {
    if (event) event.stopPropagation();
    if (!confirm("Are you sure you want to delete this profile?")) return;

    try {
        await fetch("/delete_character", {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ id })
        });
        selectedCharacterIds.delete(id);
        fetchCharacters(); // Full refresh to update allCharacters cache
    } catch (e) { alert("Delete failed."); }
}

function toggleCharacterSelection(char) {
    if (selectedCharacterIds.has(char.id)) {
        selectedCharacterIds.delete(char.id);
    } else {
        selectedCharacterIds.add(char.id);
    }
    renderCharacters();
}

function updateActiveCharBar(allChars) {
    const bar = document.getElementById("active-characters");
    if (!bar) return;
    bar.innerHTML = "";

    allChars.filter(c => selectedCharacterIds.has(c.id)).forEach(char => {
        const chip = document.createElement("span");
        chip.className = "char-chip active";
        chip.innerText = char.name;
        chip.onclick = () => toggleCharacterSelection(char);
        bar.appendChild(chip);
    });
}

// --- Generation & Metadata Streaming ---

async function generate(event) {
    const storyline = document.getElementById("story-input").value.trim();
    const location = document.getElementById("story-location").value.trim();
    const bgm = document.getElementById("story-bgm").value.trim();

    if (!storyline) return alert("Please enter a story idea.");

    const btn = document.querySelector(".cta");
    const screenplayEl = document.getElementById("screenplay");
    const historyList = document.getElementById("history-list");

    try {
        if (btn) { btn.disabled = true; btn.innerText = "⏳ GENERATING..."; }
        if (screenplayEl) screenplayEl.innerText = "";

        const response = await fetch("/generate_story", {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                storyline,
                character_ids: Array.from(selectedCharacterIds), // Send selected IDs for injection
                location: location,
                bgm: bgm
            })
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

// --- Translation ---
async function translateScript() {
    const screenplayEl = document.getElementById("screenplay");
    const targetLang = document.getElementById("target-lang")?.value;
    if (!screenplayEl || !screenplayEl.innerText.trim()) {
        return alert("Nothing to translate.");
    }
    if (!targetLang) {
        return alert("Please select a target language.");
    }

    const btn = document.getElementById("translate-btn");
    try {
        if (btn) { btn.disabled = true; btn.innerText = "Translating..."; }
        const res = await fetch("/translate_script", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ script: screenplayEl.innerText, target_language: targetLang })
        });
        const data = await res.json();
        if (res.ok) {
            // replace existing text with translation
            screenplayEl.innerText = data.translated;
        } else {
            alert(data.error || "Translation failed.");
        }
    } catch (e) {
        alert("Translation error.");
    } finally {
        if (btn) { btn.disabled = false; btn.innerText = "Translate"; }
    }
}

// --- Downloads ---
function download(format) {
    const screenplayText = document.getElementById("screenplay")?.innerText;
    const locationValue = document.getElementById("story-location")?.value || "";
    const bgmValue = document.getElementById("story-bgm")?.value || "";

    if (!screenplayText) return alert("No content to download.");

    if (format === 'txt') {
        let content = "";

        if (locationValue || bgmValue) {
            content += "=== CINEMATIC SETTINGS ===\n";
            if (locationValue) content += `Location: ${locationValue}\n`;
            if (bgmValue) content += `BGM Tone: ${bgmValue}\n`;
            content += "========================\n\n";
        }

        // Add Character Profiles to TXT
        if (selectedCharacterIds.size > 0) {
            content += "=== CHARACTER PROFILES ===\n\n";
            allCharacters.filter(c => selectedCharacterIds.has(c.id)).forEach(char => {
                content += `${char.name.toUpperCase()}\n`;
                content += `${char.description}\n`;
                if (char.personality) content += `Personality: ${char.personality}\n`;
                content += "\n";
            });
            content += "========================\n\n";
        }

        content += "=== SCREENPLAY ===\n\n";
        content += screenplayText;

        const blob = new Blob([content], { type: "text/plain" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url; a.download = "screenplay.txt"; a.click();
        return;
    }

    const endpoint = format === 'pdf' ? '/download_pdf' : '/download_docx';
    fetch(endpoint, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            screenplay: screenplayText,
            location: locationValue,
            bgm: bgmValue,
            character_ids: Array.from(selectedCharacterIds) // Include selected character IDs
        })
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
        fetchCharacters(); // Pre-load profiles for chips/grid
    }
});