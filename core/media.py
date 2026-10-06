"""Browser-side helpers for the interview: the AI interviewer speaks (text-to-speech) and a private camera self-view.

Everything here runs in the user's browser. The camera video is only shown on screen; it is never recorded,
uploaded or sent to the AI. Text-to-speech uses the browser's built-in voices, so there is nothing to install.
"""
from __future__ import annotations

import json

import streamlit.components.v1 as components


def _js_string(text: str) -> str:
    """Safely embed text inside a <script>."""
    return json.dumps(text).replace("</", "<\\/")


def speak(text: str, height: int = 52) -> None:
    """Show a small player that reads ``text`` aloud (auto-plays when the browser allows it) with a Replay button."""
    components.html(
        f"""
<style>
  body{{margin:0;font-family:system-ui,sans-serif;}}
  button{{border:1px solid #94A3B8;background:#fff;color:#0F172A;border-radius:8px;padding:6px 12px;font-weight:600;cursor:pointer;}}
  button:hover{{background:#F1F5F9;}}
  span{{font-size:12px;color:#64748B;margin-left:8px;}}
</style>
<button id="play">🔊 Hear the question</button><button id="stop" style="margin-left:6px">⏹ Stop</button>
<span id="note"></span>
<script>
  const text = {_js_string(text)};
  const note = document.getElementById('note');
  function say() {{
    if (!('speechSynthesis' in window)) {{ note.textContent = 'Speech is not supported in this browser.'; return; }}
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.lang = 'en-US'; u.rate = 0.98;
    const voices = window.speechSynthesis.getVoices();
    const pick = voices.find(v => /en[-_]/i.test(v.lang) && /natural|google|samantha|zira|aria/i.test(v.name)) || voices.find(v => /^en/i.test(v.lang));
    if (pick) u.voice = pick;
    u.onstart = () => note.textContent = 'Speaking...';
    u.onend = () => note.textContent = '';
    window.speechSynthesis.speak(u);
  }}
  document.getElementById('play').onclick = say;
  document.getElementById('stop').onclick = () => window.speechSynthesis.cancel();
  window.speechSynthesis.onvoiceschanged = () => {{}};
  setTimeout(say, 400);  // auto-play; if the browser blocks it, click the button
</script>
""",
        height=height,
    )


def camera_panel(height: int = 250) -> None:
    """Live camera self-view with Start/Stop. Video stays in the browser."""
    components.html(
        """
<style>
  body{margin:0;font-family:system-ui,sans-serif;}
  video{width:100%;border-radius:12px;background:#0F172A;border:1px solid #94A3B8;transform:scaleX(-1);}
  button{border:1px solid #94A3B8;background:#fff;color:#0F172A;border-radius:8px;padding:6px 12px;font-weight:600;cursor:pointer;margin-top:6px;}
  button:hover{background:#F1F5F9;}
  p{font-size:12px;color:#64748B;margin:6px 0 0 0;}
</style>
<video id="v" autoplay playsinline muted></video>
<div><button id="on">📷 Turn on camera</button><button id="off">Turn off</button></div>
<p id="msg">Your video stays on your device. It is not recorded or uploaded.</p>
<script>
  const v = document.getElementById('v'), msg = document.getElementById('msg');
  let stream = null;
  async function start() {
    try {
      stream = await navigator.mediaDevices.getUserMedia({video: {width: 640, height: 480}, audio: false});
      v.srcObject = stream;
      msg.textContent = 'Camera is on. Video stays on your device.';
    } catch (e) {
      msg.textContent = 'Camera blocked or not found (' + e.name + '). Click the camera icon in the address bar and allow access, then press the button again.';
    }
  }
  function stop() { if (stream) { stream.getTracks().forEach(t => t.stop()); stream = null; v.srcObject = null; } msg.textContent = 'Camera is off.'; }
  document.getElementById('on').onclick = start;
  document.getElementById('off').onclick = stop;
  start();
</script>
""",
        height=height,
    )
