import os
from flask import Flask, render_template_string
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'chameleon_secret_key'

# 16MB media serheti
socketio = SocketIO(app, cors_allowed_origins="*", max_http_buffer_size=16 * 1024 * 1024)

SECRET_PASSCODE = "2021"

# Hatlary RAM-da saklamak üçin struktura
# Structure: { msg_id: { 'data': data, 'read_by': set() } }
messages_db = {}
msg_counter = 0

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Google</title>
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: Roboto, Arial, sans-serif; }
        body { background: #202124; color: #e8eaed; display: flex; flex-direction: column; height: 100vh; }

        #google-page { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; padding: 20px; }
        .logo { font-size: 56px; font-weight: bold; margin-bottom: 25px; letter-spacing: -2px; }
        .logo span:nth-child(1) { color: #4285F4; }
        .logo span:nth-child(2) { color: #EA4335; }
        .logo span:nth-child(3) { color: #FBBC05; }
        .logo span:nth-child(4) { color: #4285F4; }
        .logo span:nth-child(5) { color: #34A853; }
        .logo span:nth-child(6) { color: #EA4335; }

        .search-box { width: 100%; max-width: 580px; }
        .search-input { width: 100%; height: 46px; background: #202124; border: 1px solid #5f6368; border-radius: 24px; padding: 0 20px; font-size: 16px; color: #fff; outline: none; }

        #chat-page { display: none; flex-direction: column; height: 100%; max-width: 600px; margin: 0 auto; width: 100%; background: #121212; }
        .chat-header { padding: 15px; background: #1f1f1f; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #333; }
        .chat-messages { flex: 1; padding: 15px; overflow-y: auto; display: flex; flex-direction: column; gap: 12px; }

        .msg { max-width: 80%; padding: 10px 14px; border-radius: 12px; font-size: 14px; word-wrap: break-word; }
        .msg.me { background: #1a73e8; color: #fff; align-self: flex-end; }
        .msg.peer { background: #2d2d2d; color: #e8eaed; align-self: flex-start; }

        .msg img, .msg video { max-width: 100%; border-radius: 8px; margin-top: 5px; display: block; }
        .msg audio { max-width: 100%; margin-top: 5px; }

        .chat-input-box { padding: 10px; background: #1f1f1f; display: flex; gap: 6px; align-items: center; }
        .chat-input-box input[type="text"] { flex: 1; height: 40px; background: #2d2d2d; border: none; border-radius: 20px; padding: 0 15px; color: #fff; outline: none; }
        .chat-input-box button { background: #1a73e8; border: none; color: #fff; padding: 0 16px; height: 40px; border-radius: 20px; font-weight: bold; cursor: pointer; }

        .btn-icon { background: #333; color: #fff; width: 38px; height: 38px; border-radius: 50%; display: flex; align-items: center; justify-content: center; cursor: pointer; border: none; }
        #mediaInput { display: none; }
        .exit-btn { background: #d93025; border: none; color: white; padding: 6px 12px; border-radius: 6px; cursor: pointer; }
    </style>
</head>
<body>

    <div id="google-page">
        <div class="logo">
            <span>G</span><span>o</span><span>o</span><span>g</span><span>l</span><span>e</span>
        </div>
        <div class="search-box">
            <input type="text" id="searchInput" class="search-input" placeholder="Search Google or type a URL" onkeypress="checkCode(event)">
        </div>
    </div>

    <div id="chat-page">
        <div class="chat-header">
            <span><strong>Self-Destruct Secure Chat</strong></span>
            <button class="exit-btn" onclick="exitChat()">Exit</button>
        </div>
        <div class="chat-messages" id="msgBox"></div>
        <div class="chat-input-box">
            <label class="btn-icon" title="Attach Media (Image/Video/Audio)">
                📁
                <input type="file" id="mediaInput" accept="image/*,video/*,audio/*" onchange="sendMedia(this)">
            </label>
            <input type="text" id="msgInput" placeholder="Message..." onkeypress="sendOnEnter(event)">
            <button onclick="sendMessage()">Send</button>
        </div>
    </div>

    <script>
        const socket = io();
        const PASSCODE = "2021";
        let myClientId = Math.random().toString(36).substring(2, 9);

        function checkCode(e) {
            if (e.key === 'Enter') {
                const val = document.getElementById('searchInput').value.trim();
                if (val === PASSCODE) {
                    document.getElementById('google-page').style.display = 'none';
                    document.getElementById('chat-page').style.display = 'flex';
                    document.getElementById('searchInput').value = '';
                    socket.emit('request_history', { clientId: myClientId });
                } else {
                    window.location.href = "https://www.google.com/search?q=" + encodeURIComponent(val);
                }
            }
        }

        socket.on('load_history', (unreadMessages) => {
            unreadMessages.forEach(msg => {
                appendMsgToBox(msg.data, 'peer');
                socket.emit('mark_read', { msgId: msg.id, clientId: myClientId });
            });
        });

        function sendMessage() {
            const input = document.getElementById('msgInput');
            const text = input.value.trim();
            if (text) {
                const data = { type: 'text', content: text, senderId: myClientId };
                appendMsgToBox(data, 'me');
                socket.emit('send_msg', data);
                input.value = '';
            }
        }

        function sendMedia(input) {
            const file = input.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    let fileType = 'file';
                    if (file.type.startsWith('image/')) fileType = 'image';
                    else if (file.type.startsWith('video/')) fileType = 'video';
                    else if (file.type.startsWith('audio/')) fileType = 'audio';

                    const data = { type: fileType, content: e.target.result, fileName: file.name, senderId: myClientId };
                    appendMsgToBox(data, 'me');
                    socket.emit('send_msg', data);
                };
                reader.readAsDataURL(file);
                input.value = '';
            }
        }

        function sendOnEnter(e) {
            if (e.key === 'Enter') sendMessage();
        }

        socket.on('receive_msg', (msg) => {
            appendMsgToBox(msg.data, 'peer');
            socket.emit('mark_read', { msgId: msg.id, clientId: myClientId });
        });

        function appendMsgToBox(data, sender) {
            const box = document.getElementById('msgBox');
            const div = document.createElement('div');
            div.className = `msg ${sender}`;

            if (data.type === 'text') {
                div.textContent = data.content;
            } else if (data.type === 'image') {
                const img = document.createElement('img');
                img.src = data.content;
                div.appendChild(img);
            } else if (data.type === 'video') {
                const video = document.createElement('video');
                video.controls = true;
                video.src = data.content;
                div.appendChild(video);
            } else if (data.type === 'audio') {
                const audio = document.createElement('audio');
                audio.controls = true;
                audio.src = data.content;
                div.appendChild(audio);
            }

            box.appendChild(div);
            box.scrollTop = box.scrollHeight;
        }

        function exitChat() {
            document.getElementById('msgBox').innerHTML = '';
            document.getElementById('chat-page').style.display = 'none';
            document.getElementById('google-page').style.display = 'flex';
        }
    </script>
</body>
</html>
"""


@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


@socketio.on('send_msg')
def handle_message(data):
    global msg_counter
    msg_counter += 1
    msg_id = msg_counter

    # Message status initialized
    messages_db[msg_id] = {
        'data': data,
        'read_by': set([data['senderId']])  # Sender already read it
    }

    # Broadcast to peers
    emit('receive_msg', {'id': msg_id, 'data': data}, broadcast=True, include_self=False)


@socketio.on('request_history')
def handle_history_request(data):
    client_id = data.get('clientId')
    unread = []

    for msg_id, msg_info in list(messages_db.items()):
        if client_id not in msg_info['read_by']:
            unread.append({'id': msg_id, 'data': msg_info['data']})

    emit('load_history', unread)


@socketio.on('mark_read')
def handle_mark_read(data):
    msg_id = data.get('msgId')
    client_id = data.get('clientId')

    if msg_id in messages_db:
        messages_db[msg_id]['read_by'].add(client_id)
        # Biri okap çykan badyna RAM-dan doly pozýarys (Self-destruct)
        if len(messages_db[msg_id]['read_by']) >= 2:
            del messages_db[msg_id]


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host='0.0.0.0', port=port)