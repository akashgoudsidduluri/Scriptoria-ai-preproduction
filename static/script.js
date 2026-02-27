function showModal() {
    document.getElementById("modal").classList.add("visible");
    document.getElementById("username").focus();
}

function closeModal() {
    document.getElementById("modal").classList.remove("visible");
}

async function enter() {
    const username = document.getElementById("username").value.trim();
    if (!username) {
        alert("Please enter your name");
        return;
    }

    try {
        await fetch("/set_username", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username })
        });
        window.location.href = "/dashboard";
    } catch (e) {
        console.error("Error setting username:", e);
        alert("Error: " + e.message);
    }
}

async function generate() {
    console.log("generate clicked");

    const storyline = document.getElementById("story").value.trim();
    if (!storyline) {
        alert("Please enter a story idea");
        return;
    }

    const btn = event?.target;
    const originalText = btn?.innerText || "Generate Content";
    const screenplayEl = document.getElementById("screenplay");
    
    try {
        if (btn) {
            btn.innerText = "⏳ Generating...";
            btn.disabled = true;
        }
        
        screenplayEl.innerText = "🎬 Streaming response...\n";
        
        console.log("Sending request to /generate_story with storyline:", storyline.substring(0, 50) + "...");
        
        const res = await fetch("/generate_story", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ storyline })
        });

        console.log("Response received, status:", res.status);

        if (!res.ok) {
            const errorMsg = await res.text();
            console.error("Server error:", res.status, errorMsg);
            alert("Error " + res.status + ": " + errorMsg);
            screenplayEl.innerText = "❌ Error: " + errorMsg;
            if (btn) {
                btn.innerText = originalText;
                btn.disabled = false;
            }
            return;
        }

        // Handle streaming response (Server-Sent Events)
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        screenplayEl.innerText = "";
        
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            const chunk = decoder.decode(value);
            const lines = chunk.split('\n');
            
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.slice(6));
                        if (data.text) {
                            screenplayEl.innerText += data.text;
                            // Auto-scroll to bottom
                            screenplayEl.scrollTop = screenplayEl.scrollHeight;
                        }
                    } catch (e) {
                        console.warn("Could not parse SSE data:", line);
                    }
                }
            }
        }
        
        console.log("Streaming complete");
        
        if (btn) {
            btn.innerText = originalText;
            btn.disabled = false;
        }
    } catch (e) {
        console.error("Generate catch error:", e.message, e.stack);
        alert("Error: " + e.message + "\n\nMake sure Flask and Ollama are running!");
        screenplayEl.innerText = "❌ Error: " + e.message;
        if (btn) {
            btn.innerText = originalText;
            btn.disabled = false;
        }
    }
}

function download(format) {
    const screenplayText = document.getElementById("screenplay").innerText;
    if (!screenplayText || screenplayText === "No screenplay generated") {
        alert("No content to download. Generate a screenplay first.");
        return;
    }

    const blob = new Blob([screenplayText], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `screenplay.${format}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

// Event listeners
document.addEventListener("DOMContentLoaded", () => {
    const usernameInput = document.getElementById("username");
    if (usernameInput) {
        usernameInput.addEventListener("keypress", (e) => {
            if (e.key === "Enter") enter();
        });
    }

    const storyInput = document.getElementById("story");
    if (storyInput) {
        storyInput.addEventListener("keypress", (e) => {
            if (e.key === "Enter" && e.ctrlKey) generate();
        });
    }

    // Close modal on Escape key
    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape") {
            closeModal();
        }
    });
});