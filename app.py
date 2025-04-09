from flask import Flask, jsonify, request, send_file, render_template_string
import os, shutil

app = Flask(__name__)
current_path = os.getcwd()
clipboard = None

HTML = '''
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>GUI File Explorer</title>
  <style>
    body { font-family: sans-serif; background: #f4f4f4; padding: 30px; }
    h2 { margin-bottom: 20px; }
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 20px; }
    .item { background: white; border: 1px solid #ccc; border-radius: 8px; padding: 10px; text-align: center; box-shadow: 1px 1px 4px rgba(0,0,0,0.1); cursor: pointer; position: relative; }
    .item:hover { background: #e6f0ff; }
    .dropdown-button {
      position: absolute;
      top: 8px;
      right: 10px;
      cursor: pointer;
      font-size: 18px;
      background: transparent;
      border: none;
    }
    .dropdown-menu {
      position: absolute;
      top: 35px;
      right: 10px;
      background: white;
      border: 1px solid #ccc;
      border-radius: 4px;
      display: none;
      z-index: 100;
    }
    .dropdown-menu option {
      padding: 5px;
    }
    .toolbar { margin-bottom: 20px; }
    button { padding: 10px 15px; margin-right: 10px; }
  </style>
  <script>
    async function fetchFiles() {
      const res = await fetch('/list');
      const data = await res.json();
      const grid = document.getElementById('file-grid');
      grid.innerHTML = '';

      if (data.path !== "/") {
        const up = document.createElement('div');
        up.className = 'item';
        up.innerHTML = '⬆️ .. (up)';
        up.onclick = () => changeDir('..');
        grid.appendChild(up);
      }

      data.items.forEach(name => {
        const div = document.createElement('div');
        div.className = 'item';
        div.innerHTML = name;

        const gear = document.createElement('button');
        gear.className = 'dropdown-button';
        gear.innerHTML = '⚙️';

        const menu = document.createElement('select');
        menu.className = 'dropdown-menu';
        menu.innerHTML = `
          <option selected disabled>⚙ Options</option>
          <option value="open">📂 Open</option>
          <option value="del">🗑️ Delete</option>
          <option value="ren">✏️ Rename</option>
          <option value="cp">📋 Copy</option>
          <option value="dl">⬇️ Download</option>
        `;

        div.onmouseenter = () => {
          gear.style.display = 'inline';
        };
        div.onmouseleave = () => {
          gear.style.display = 'none';
          menu.style.display = 'none';
        };

        gear.onclick = (e) => {
          e.stopPropagation();
          document.querySelectorAll('.dropdown-menu').forEach(m => m.style.display = 'none');
          menu.style.display = 'block';
        };

        menu.onchange = () => {
          const action = menu.value;
          menu.selectedIndex = 0;
          menu.style.display = 'none';
          if (action === 'open') changeDir(name);
          else if (action === 'del') sendAction('del', name);
          else if (action === 'ren') {
            const newName = prompt('New name:', name);
            if (newName) sendAction('ren', name + '|' + newName);
          }
          else if (action === 'cp') sendAction('cp', name);
          else if (action === 'dl') window.location.href = '/download/' + encodeURIComponent(name);
        };

        div.appendChild(gear);
        div.appendChild(menu);
        grid.appendChild(div);
      });

      document.getElementById('path').innerText = "📁 " + data.path;
    }

    async function changeDir(name) {
      await fetch('/cd', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name })
      });
      fetchFiles();
    }

    async function sendAction(cmd, target) {
      await fetch('/action', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cmd, target })
      });
      fetchFiles();
    }

    function pasteClipboard() {
      sendAction('paste', '');
    }

    function createFolder() {
      const name = prompt('Folder name:');
      if (name) sendAction('mkdir', name);
    }

    function createFile() {
      const name = prompt('File name:');
      if (name) sendAction('touch', name);
    }

    window.onload = fetchFiles;
  </script>
</head>
<body>
  <h2>🗂️ GUI File Explorer</h2>
  <div class="toolbar">
    <span id="path"></span><br><br>
    <button onclick="createFolder()">📁 New Folder</button>
    <button onclick="createFile()">📄 New File</button>
    <button onclick="pasteClipboard()">📋 Paste</button>
  </div>
  <div id="file-grid" class="grid"></div>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/list')
def list_files():
    items = os.listdir(current_path)
    return jsonify({"path": current_path, "items": items})

@app.route('/cd', methods=['POST'])
def change_dir():
    global current_path
    data = request.json
    name = data['name']
    if name == '..':
        current_path = os.path.abspath(os.path.join(current_path, '..'))
    else:
        new_path = os.path.join(current_path, name)
        if os.path.isdir(new_path):
            current_path = new_path
    return ('', 204)

@app.route('/action', methods=['POST'])
def action():
    global current_path, clipboard
    data = request.json
    cmd = data['cmd']
    target = data['target']
    def full(p): return os.path.join(current_path, p)

    try:
        if cmd == 'del':
            path = full(target)
            if os.path.isdir(path): shutil.rmtree(path)
            else: os.remove(path)

        elif cmd == 'ren':
            old, new = target.split('|')
            os.rename(full(old), full(new))

        elif cmd == 'cp':
            clipboard = full(target)

        elif cmd == 'paste':
            if clipboard:
                name = os.path.basename(clipboard)
                dst = full(f'copy_of_{name}')
                if os.path.isdir(clipboard): shutil.copytree(clipboard, dst)
                else: shutil.copy2(clipboard, dst)

        elif cmd == 'mkdir':
            os.makedirs(full(target), exist_ok=True)

        elif cmd == 'touch':
            open(full(target), 'w').close()

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return ('', 204)

@app.route('/download/<path:name>')
def download(name):
    file_path = os.path.join(current_path, name)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    return 'File not found', 404

if __name__ == '__main__':
    app.run(debug=True, port=8000)
