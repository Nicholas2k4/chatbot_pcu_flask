/* ------------------------- DOM refs ------------------------- */
const $ = s => document.querySelector(s);
const chatBtn = $('#chat-toggle');
const chatModal = $('#chat-modal');
const closeBtn = $('#close-btn');
const chatWin = $('#chat-window');
const chatForm = $('#chat-form');
const chatInput = $('#chat-input');

/* Markdown helper */
const md = txt => marked.parse(txt);

/* --------- client-side history (mulai dgn sapaan awal) ------- */
const history = [
    {
        role: 'assistant',
        content: 'Halo! Saya PCU Chatbot 🤖\nAda yang bisa saya bantu hari ini?'
    }
];

/* --------------------- modal toggle -------------------------- */
chatBtn.addEventListener('click', () => chatModal.classList.toggle('hidden'));
closeBtn.addEventListener('click', () => chatModal.classList.add('hidden'));

/* -------------------- bubble helpers ------------------------- */
function addMessage(text, sender, isHtml = false) {
    const wrap = document.createElement('div'); wrap.className = `msg ${sender}`;
    const bub = document.createElement('div'); bub.className = 'bubble';
    if (isHtml) bub.innerHTML = text; else bub.textContent = text;
    wrap.appendChild(bub); chatWin.appendChild(wrap);
    chatWin.scrollTop = chatWin.scrollHeight;
    return wrap;
}

/* loader */
function addLoader() {
    const w = document.createElement('div'); w.className = 'msg bot'; w.id = 'loader';
    const b = document.createElement('div'); b.className = 'bubble';
    const l = document.createElement('div'); l.className = 'loader';
    l.innerHTML = '<div></div><div></div><div></div>'; b.appendChild(l); w.appendChild(b);
    chatWin.appendChild(w); chatWin.scrollTop = chatWin.scrollHeight;
}
function removeLoader() { const l = $('#loader'); if (l) l.remove(); }

/* typing animations */
function typeText(text) {
    return new Promise(res => {
        const chars = [...text]; let out = '';
        const bub = addMessage('', 'bot').querySelector('.bubble');
        const t = setInterval(() => {
            out += chars.shift() || ''; bub.textContent = out; chatWin.scrollTop = chatWin.scrollHeight;
            if (!chars.length) { clearInterval(t); res(); }
        }, 15);
    });
}
async function typeMD(text) {
    const words = text.split(/(\s+)/); let out = '';
    const bub = addMessage('', 'bot', true).querySelector('.bubble');
    for (const w of words) {
        out += w; bub.innerHTML = md(out); chatWin.scrollTop = chatWin.scrollHeight;
        await new Promise(r => setTimeout(r, 25));
    }
}

/* -------------------- form submit ---------------------------- */
chatForm.addEventListener('submit', async e => {
    e.preventDefault();
    const text = chatInput.value.trim();
    if (!text) return;

    /* tampilkan & log history */
    addMessage(text, 'user'); history.push({ role: 'user', content: text });
    chatInput.value = ''; addLoader();

    try {
        const res = await fetch('/chat', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: text, history })
        });
        const data = await res.json();
        removeLoader();

        const isMD = /\n|[#*-]{2,}/.test(data.response);
        if (isMD) await typeMD(data.response); else await typeText(data.response);

        history.push({ role: 'assistant', content: data.response });
    } catch (err) {
        removeLoader(); addMessage('Error: ' + err.message, 'bot');
    }
});
