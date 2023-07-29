import os
import random
import string
from flask import Flask, render_template
from flask_socketio import SocketIO, emit, join_room, leave_room
from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaStreamTrack
from av import VideoFrame

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
socketio = SocketIO(app, async_mode='gevent')

# Dictionary to store active rooms and their participants
active_rooms = {}

# Generate a random room ID
def generate_room_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('join_room')
def join_video_room(data):
    username = data['username']
    room_id = data.get('room_id', generate_room_id())
    join_room(room_id)

    if room_id not in active_rooms:
        active_rooms[room_id] = []

    active_rooms[room_id].append(username)

    emit('user_joined', {'username': username}, room=room_id)
    emit('active_users', {'users': active_rooms[room_id]}, room=room_id, include_self=False)

@socketio.on('leave_room')
def leave_video_room(data):
    username = data['username']
    room_id = data['room_id']
    leave_room(room_id)

    if room_id in active_rooms:
        active_rooms[room_id].remove(username)

    emit('user_left', {'username': username}, room=room_id)
    emit('active_users', {'users': active_rooms[room_id]}, room=room_id, include_self=False)

@socketio.on('sdp')
async def sdp(data):
    pc = get_peer_connection(data)
    if data['type'] == 'offer':
        await pc.setRemoteDescription(RTCSessionDescription(sdp=data['sdp'], type='offer'))
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)
        await socketio.emit('sdp', {
            'type': 'answer',
            'sdp': pc.localDescription.sdp,
            'pc_id': data['pc_id'],
            'room_id': data['room_id'],
            'username': data['username']
        })
    elif data['type'] == 'answer':
        await pc.setRemoteDescription(RTCSessionDescription(sdp=data['sdp'], type='answer'))

def get_peer_connection(data):
    pc = RTCPeerConnection()
    @pc.on('datachannel')
    def on_datachannel(channel):
        @channel.on('message')
        def on_message(message):
            emit('data_channel_message', {'message': message})
    pc_id = data['pc_id']
    pcs[pc_id] = pc
    pc.pc_id = pc_id
    pc.username = data['username']
    return pc

if __name__ == '__main__':
    socketio.run(app, debug=True)
