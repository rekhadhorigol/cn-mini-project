console.log("JS LOADED");

const socket = io();

let name = "";


// ============================
// GAME SELECTOR
// ============================
function startGame(gameType){

    if(!name){
        name = prompt("Enter your player name");

        if(!name || name.trim() === ""){
            name = "Player" + Math.floor(Math.random()*1000);
        }
    }

    let container = document.getElementById("gameContainer");
    document.getElementById("multiplayerUI").style.display = "none";

    container.innerHTML = "";

    if(gameType === "click") loadClickRace();
    else if(gameType === "guess") loadGuessMulti();
    else if(gameType === "xox"){
        loadXOXSimple();
        // Request current board state (handles reconnect mid-game)
        socket.emit("xox_reset");
    }
    else if(gameType === "multiplayer"){
        document.getElementById("multiplayerUI").style.display = "block";
        createPlayer(name);
        // Announce join so other players see you appear
        socket.emit("send_message", {message: name + " joined the game", player: name});
    }
}


// ============================
// ⚡ CLICK RACE
// ============================
function loadClickRace(){

    let container = document.getElementById("gameContainer");

    container.innerHTML = `
        <h3>Click Race ⚡</h3>
        <button id="clickBtn">CLICK FAST</button>
        <div id="leaderboard"></div>
    `;

    let myScore = 0;

    document.getElementById("clickBtn").onclick = function(){
        myScore++;
        socket.emit("click_update", {name: name, score: myScore});

        if(myScore === 20){
            alert("🏆 " + name + " wins!");
        }
    };

    socket.off("click_update");

    socket.on("click_update", function(scores){

        let text = "<h4>Leaderboard:</h4>";

        for(let p in scores){
            text += p + ": " + scores[p] + "<br>";
        }

        document.getElementById("leaderboard").innerHTML = text;
    });
}


// ============================
// 🔢 GUESS GAME
// ============================
function loadGuessMulti(){

    let container = document.getElementById("gameContainer");

    container.innerHTML = `
        <h3>Guess Game 🔢 (1-10)</h3>
        <input id="guessInput" type="number" min="1" max="10" placeholder="1-10">
        <button onclick="sendGuess()">Guess</button>
        <p id="result"></p>
    `;

    window.sendGuess = function(){
        let input = document.getElementById("guessInput");
        let guess = input.value;
        if(!guess) return;
        socket.emit("guess", {name: name, guess: guess});
        input.value = "";
    };

    document.getElementById("guessInput").addEventListener("keydown", function(e){
        if(e.key === "Enter") sendGuess();
    });

    socket.off("guess_result");

    socket.on("guess_result", function(msg){
        document.getElementById("result").innerText = msg;
    });
}


// ============================
// ❌⭕ FINAL XOX
// ============================
function loadXOXSimple(){

    let container = document.getElementById("gameContainer");

    container.innerHTML = `
        <h3>XOX Multiplayer ❌⭕</h3>
        <p id="turn"></p>
    `;

    let cells = [];
    let gameOver = false;

    for(let i=0;i<9;i++){

        let btn = document.createElement("button");
        btn.style.width="60px";
        btn.style.height="60px";
        btn.style.fontSize="20px";

        btn.onclick = function(){
            if(!gameOver){
                socket.emit("xox_move_simple", {
                    index: i,
                    player: name
                });
            }
        };

        container.appendChild(btn);
        cells.push(btn);

        if((i+1)%3===0){
            container.appendChild(document.createElement("br"));
        }
    }

    socket.off("xox_update_simple");

    socket.on("xox_update_simple", function(data){

        let {board, turn, result, winnerName, winLine} = data;

        for(let i=0;i<9;i++){
            cells[i].innerText = board[i];
            cells[i].style.background = "white";
        }

        document.getElementById("turn").innerText =
            "Turn: " + turn;

        // highlight winning line
        if(winLine){
            winLine.forEach(i=>{
                cells[i].style.background = "lightgreen";
            });
        }

        if(result && !gameOver){

            gameOver = true;

            if(result === "draw"){
                setTimeout(()=>alert("Draw 🤝"),100);
            } else {

                if(winnerName === name){
                    setTimeout(()=>alert("🎉 You WIN!"),100);
                } else {
                    setTimeout(()=>alert("❌ You LOSE! Winner: " + winnerName),100);
                }
            }

            setTimeout(()=>location.reload(),2000);
        }
    });
}


// ============================
// 🎮 MOVEMENT GAME
// ============================

let players = {};

function createPlayer(playerName){

    if(players[playerName]) return;

    let wrapper = document.createElement("div");
    wrapper.style.position = "absolute";

    let label = document.createElement("div");
    label.innerText = playerName;
    label.style.fontSize = "12px";
    label.style.textAlign = "center";

    let avatar = document.createElement("div");

    let emojis = ["👨","👩","🧑","🧔","👱"];
    avatar.innerText = emojis[Math.floor(Math.random()*emojis.length)];
    avatar.style.fontSize = "20px";

    wrapper.appendChild(label);
    wrapper.appendChild(avatar);

    wrapper.style.left = Math.random()*300 + "px";
    wrapper.style.top = Math.random()*120 + "px";

    let playersDiv = document.getElementById("players");
    if(playersDiv){
        playersDiv.appendChild(wrapper);
    }

    players[playerName] = wrapper;
}


// movement
function movePlayer(playerName, direction){

    if(!players[playerName]){
        createPlayer(playerName);
    }

    let player = players[playerName];

    let x = player.offsetLeft;
    let y = player.offsetTop;

    if(direction === "UP") y -= 10;
    if(direction === "DOWN") y += 10;
    if(direction === "LEFT") x -= 10;
    if(direction === "RIGHT") x += 10;

    x = Math.max(0, Math.min(360, x));
    y = Math.max(0, Math.min(160, y));

    player.style.left = x + "px";
    player.style.top = y + "px";
}


// shooting
function shoot(playerName){

    if(!players[playerName]) return;

    let player = players[playerName];

    let bullet = document.createElement("div");
    bullet.innerText = "🔴";

    bullet.style.position = "absolute";
    bullet.style.left = player.offsetLeft + 20 + "px";
    bullet.style.top = player.offsetTop + 10 + "px";

    document.getElementById("players").appendChild(bullet);

    let pos = player.offsetLeft + 20;

    let interval = setInterval(function(){

        pos += 10;
        bullet.style.left = pos + "px";

        if(pos > 400){
            clearInterval(interval);
            bullet.remove();
        }

    }, 30);
}


// controls
function sendCommand(cmd){

    let message = "";

    if(cmd === "left")  message = name + " moved LEFT";
    if(cmd === "right") message = name + " moved RIGHT";
    if(cmd === "up")    message = name + " moved UP";
    if(cmd === "down")  message = name + " moved DOWN";
    if(cmd === "shoot") message = name + " shot";

    // Apply locally immediately (client-side prediction)
    if(cmd === "shoot") shoot(name);
    else movePlayer(name, cmd.toUpperCase());

    socket.emit("send_message", {message: message, player: name});
}


// ⌨️ Keyboard controls (Arrow keys + WASD + Space)
let keysHeld = {};

document.addEventListener("keydown", function(e){
    if(keysHeld[e.key]) return; // prevent repeat spam
    keysHeld[e.key] = true;

    // Only active when movement game is visible
    if(document.getElementById("multiplayerUI").style.display === "none") return;

    // Don't capture keys when typing in chat input
    if(document.activeElement === document.getElementById("input")) return;

    let cmd = null;
    if(e.key === "ArrowUp"    || e.key === "w" || e.key === "W") cmd = "up";
    if(e.key === "ArrowDown"  || e.key === "s" || e.key === "S") cmd = "down";
    if(e.key === "ArrowLeft"  || e.key === "a" || e.key === "A") cmd = "left";
    if(e.key === "ArrowRight" || e.key === "d" || e.key === "D") cmd = "right";
    if(e.key === " " || e.key === "f"|| e.key === "F")            cmd = "shoot";

    if(cmd){
        e.preventDefault();
        sendCommand(cmd);
    }
});

document.addEventListener("keyup", function(e){
    keysHeld[e.key] = false;
});


// chat
function sendChat(){
    let input = document.getElementById("input");
    let text = input.value.trim();
    if(!text) return;
    socket.emit("send_message", {message: name + ": " + text, player: name});
    input.value = "";
}

// Enter key support for chat
document.addEventListener("DOMContentLoaded", function(){
    let chatInput = document.getElementById("input");
    if(chatInput){
        chatInput.addEventListener("keydown", function(e){
            if(e.key === "Enter") sendChat();
        });
    }
});


// RECEIVE
socket.on("receive_message", function(data){

    let message = data.message;

    // Parse movement first — don't show these in chat box
    let moveMatch = message.match(/^(\S+) moved (UP|DOWN|LEFT|RIGHT)$/);
    if(moveMatch){
        movePlayer(moveMatch[1], moveMatch[2]);
        return;
    }

    // Parse shoot
    let shootMatch = message.match(/^(\S+) shot$/);
    if(shootMatch){
        shoot(shootMatch[1]);
        return;
    }

    // Parse join: spawn avatar silently
    let joinMatch = message.match(/^(.+) joined the game$/);
    if(joinMatch){
        createPlayer(joinMatch[1]);
        // Still show join in chat
    }

    // Show chat messages (and join notifications) in message box
    let msgBox = document.getElementById("messages");
    if(msgBox){
        msgBox.innerHTML += message + "<br>";
        msgBox.scrollTop = msgBox.scrollHeight;
    }
});