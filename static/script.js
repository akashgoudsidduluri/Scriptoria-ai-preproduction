async function enter(){
    const username = document.getElementById("username").value;

    await fetch("/set_username", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body: JSON.stringify({username})
    });

    window.location.href = "/dashboard";
}


async function generate(){
    const storyline = document.getElementById("story").value;

    const res = await fetch("/generate_story", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body: JSON.stringify({storyline})
    });

    const data = await res.json();

    document.getElementById("screenplay").innerText = data.screenplay;
    document.getElementById("characters").innerText = data.characters;
    document.getElementById("sound").innerText = data.sound;
}