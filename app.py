import os, io, base64, json
from flask import Flask, request, render_template_string, send_file, redirect, session
from datetime import datetime
import qrcode

app = Flask(__name__)
app.secret_key = "utesa_carnetizacion_2024"

CARPETA = "/tmp/documentos"
HISTORIAL_FILE = "/tmp/historial.json"
os.makedirs(CARPETA, exist_ok=True)

CLAVE = "utesa2026"
EXTS = {"pdf","jpg","jpeg","png","doc","docx"}
MAX_MB = 25

def ext_ok(nombre):
    return "." in nombre and nombre.rsplit(".",1)[1].lower() in EXTS

def generar_qr(url):
    qr = qrcode.QRCode(box_size=8, border=4)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()

def cargar_historial():
    if os.path.exists(HISTORIAL_FILE):
        with open(HISTORIAL_FILE) as f:
            return json.load(f)
    return []

def guardar_historial(h):
    with open(HISTORIAL_FILE, "w") as f:
        json.dump(h, f, ensure_ascii=False)

def siguiente_turno():
    h = cargar_historial()
    return len(h) + 1

LOGIN = """<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Carnetización - Acceso</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:Arial,sans-serif;background:#f0f2f5;display:flex;align-items:center;justify-content:center;min-height:100vh;padding:20px}
.card{background:white;width:100%;max-width:380px;padding:32px;border-radius:16px;box-shadow:0 4px 16px rgba(0,0,0,.1);text-align:center}
h2{color:#1a1a2e;margin-bottom:8px;font-size:22px}
p{color:#777;font-size:14px;margin-bottom:24px}
input{width:100%;padding:12px;border:1px solid #ccc;border-radius:8px;font-size:15px;margin-bottom:14px}
button{width:100%;padding:13px;background:#1a1a2e;color:white;border:none;border-radius:8px;font-size:16px;cursor:pointer}
.err{color:#c0392b;font-size:13px;margin-bottom:12px}
</style></head><body><div class="card">
<h2>📇 Carnetización UTESA</h2>
<p>Panel de la encargada</p>
{% if error %}<div class="err">Contraseña incorrecta.</div>{% endif %}
<form method="post">
  <input type="password" name="clave" placeholder="Contraseña" required>
  <button type="submit">Entrar</button>
</form>
</div></body></html>"""

PANEL = """<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">
<title>Carnetización - Panel</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:Arial,sans-serif;background:#f0f2f5;padding:24px 16px;text-align:center}
.card{background:white;max-width:580px;margin:0 auto 20px;padding:28px;border-radius:16px;box-shadow:0 4px 16px rgba(0,0,0,.1)}
h1{color:#1a1a2e;margin-bottom:6px;font-size:21px}
p{color:#666;font-size:14px;margin-bottom:10px}
img.qr{width:200px;height:200px;margin:10px 0}
.url{font-size:11px;color:#aaa;word-break:break-all}
table{width:100%;border-collapse:collapse;font-size:13px;text-align:left}
th{background:#f4f4f4;padding:9px 10px;color:#333}
td{padding:9px 10px;border-bottom:1px solid #eee;vertical-align:middle}
.btn{display:inline-block;padding:6px 12px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:600;border:none;cursor:pointer}
.btn-dl{background:#1a73e8;color:white}
.btn-del{background:#e74c3c;color:white}
.btn-logout{background:#555;color:white;font-size:13px;padding:8px 18px}
.empty{color:#999;padding:18px 0;font-size:14px}
.top{display:flex;justify-content:space-between;align-items:center;max-width:580px;margin:0 auto 14px}
.turno{display:inline-block;background:#1a1a2e;color:white;border-radius:50%;width:32px;height:32px;line-height:32px;text-align:center;font-weight:700;font-size:13px}
.nuevo{background:#fff3cd;animation:parpadeo 1s infinite}
@keyframes parpadeo{0%,100%{opacity:1}50%{opacity:0.5}}
.tabs{display:flex;gap:8px;margin-bottom:16px;justify-content:center}
.tab{padding:8px 20px;border-radius:8px;border:2px solid #ddd;cursor:pointer;font-size:14px;background:white;color:#555}
.tab.active{background:#1a1a2e;color:white;border-color:#1a1a2e}
.section{display:none}.section.active{display:block}
</style>
<audio id="alerta" src="https://www.soundjay.com/buttons/sounds/button-09.mp3" preload="auto"></audio>
</head><body>
<div class="top">
  <span style="font-size:13px;color:#555">Bienvenida 👋</span>
  <a class="btn btn-logout" href="/logout">Cerrar sesión</a>
</div>
<div class="card">
  <h1>📇 Carnetización UTESA</h1>
  <p>Los estudiantes escanean este QR para enviar documentos</p>
  <img class="qr" src="data:image/png;base64,{{ qr }}">
  <p class="url">{{ url_subida }}</p>
</div>
<div class="card">
  <div class="tabs">
    <button class="tab active" onclick="mostrar('pendientes',this)">📂 Pendientes ({{ total }})</button>
    <button class="tab" onclick="mostrar('historial',this)">📋 Historial ({{ hist_total }})</button>
  </div>
  <div id="pendientes" class="section active">
    {% if archivos %}
    <table>
      <tr><th>#</th><th>Nombre</th><th>Fecha y hora</th><th>Tamaño</th><th>Descargar</th><th>Borrar</th></tr>
      {% for a in archivos %}
      <tr class="{{ 'nuevo' if loop.first and total > 0 else '' }}">
        <td><span class="turno">{{ loop.revindex }}</span></td>
        <td style="word-break:break-all;max-width:160px">{{ a.nombre }}</td>
        <td style="white-space:nowrap">{{ a.fecha }}</td>
        <td>{{ a.tamano }}</td>
        <td><a class="btn btn-dl" href="/descargar/{{ a.archivo }}">⬇</a></td>
        <td>
          <form method="post" action="/borrar/{{ a.archivo }}" onsubmit="return confirm('¿Borrar este archivo?')">
            <button class="btn btn-del" type="submit">🗑</button>
          </form>
        </td>
      </tr>
      {% endfor %}
    </table>
    {% if total > 1 %}
    <form method="post" action="/borrar-todos" onsubmit="return confirm('¿Borrar TODOS los documentos pendientes?')" style="margin-top:16px">
      <button class="btn btn-del" style="width:100%;padding:10px;font-size:14px">🗑 Borrar todos los pendientes</button>
    </form>
    {% endif %}
    {% else %}
    <p class="empty">No hay documentos pendientes.</p>
    {% endif %}
  </div>
  <div id="historial" class="section">
    {% if historial %}
    <table>
      <tr><th>#</th><th>Nombre</th><th>Fecha y hora</th><th>Tamaño</th><th>Estado</th></tr>
      {% for h in historial|reverse %}
      <tr>
        <td><span class="turno" style="background:#888">{{ h.turno }}</span></td>
        <td style="word-break:break-all;max-width:180px">{{ h.nombre }}</td>
        <td style="white-space:nowrap">{{ h.fecha }}</td>
        <td>{{ h.tamano }}</td>
        <td style="color:#27ae60;font-weight:600">✓ Recibido</td>
      </tr>
      {% endfor %}
    </table>
    {% else %}
    <p class="empty">El historial está vacío.</p>
    {% endif %}
  </div>
</div>
<script>
function mostrar(id, btn){
  document.querySelectorAll('.section').forEach(s=>s.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  document.getElementById(id).classList.add('active');
  btn.classList.add('active');
}
var totalAnterior = {{ total }};
setInterval(function(){
  fetch('/total').then(r=>r.json()).then(d=>{
    if(d.total > totalAnterior){
      document.getElementById('alerta').play();
      totalAnterior = d.total;
      location.reload();
    }
  });
}, 5000);
</script>
</body></html>"""

FORM = """<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Enviar documento</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:Arial,sans-serif;background:#f0f2f5;padding:30px 16px}
.card{background:white;max-width:420px;margin:0 auto;padding:28px;border-radius:16px;box-shadow:0 4px 16px rgba(0,0,0,.1)}
h2{color:#1a1a2e;text-align:center;margin-bottom:20px;font-size:20px}
label{display:block;margin:16px 0 6px;font-size:14px;color:#444;font-weight:600}
input{width:100%;padding:11px;border:1px solid #ccc;border-radius:8px;font-size:15px}
button{width:100%;margin-top:22px;padding:15px;background:#1a73e8;color:white;border:none;border-radius:8px;font-size:17px;cursor:pointer}
.info{font-size:12px;color:#888;margin-top:4px}
.err-size{color:#c0392b;font-size:13px;margin-top:6px;display:none}
</style></head><body><div class="card">
<h2>📄 Enviar documento a imprimir</h2>
<form method="post" enctype="multipart/form-data" onsubmit="return validar()">
  <label>Tu nombre</label>
  <input type="text" name="nombre" id="nombre" placeholder="Ej. Juan Pérez" required>
  <label>Selecciona el documento</label>
  <input type="file" name="doc" id="doc" accept=".pdf,.jpg,.jpeg,.png,.doc,.docx" required onchange="mostrarPeso()">
  <div class="info">Formatos: PDF, Word, JPG, PNG &nbsp;•&nbsp; Máximo: 25 MB</div>
  <div id="peso" class="info" style="color:#1a73e8;margin-top:4px"></div>
  <div id="err-size" class="err-size">⚠ El archivo supera los 25 MB. Elige uno más pequeño.</div>
  <button type="submit">📤 Enviar documento</button>
</form>
</div>
<script>
function mostrarPeso(){
  var f = document.getElementById('doc').files[0];
  var err = document.getElementById('err-size');
  var info = document.getElementById('peso');
  if(f){
    var mb = (f.size/1024/1024).toFixed(2);
    info.textContent = 'Tamaño: ' + mb + ' MB';
    err.style.display = f.size > 25*1024*1024 ? 'block' : 'none';
  }
}
function validar(){
  var f = document.getElementById('doc').files[0];
  if(f && f.size > 25*1024*1024){
    document.getElementById('err-size').style.display='block';
    return false;
  }
  return true;
}
</script>
</body></html>"""

CONFIRMACION = """<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Documento enviado</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:Arial,sans-serif;background:#f0f2f5;padding:40px 16px;text-align:center}
.card{background:white;max-width:400px;margin:0 auto;padding:36px 28px;border-radius:16px;box-shadow:0 4px 16px rgba(0,0,0,.1)}
.turno{font-size:80px;font-weight:700;color:#1a1a2e;line-height:1;margin:16px 0}
h2{color:#1a1a2e;font-size:20px;margin-bottom:8px}
p{color:#666;font-size:15px;margin-bottom:6px}
.ok{color:#27ae60;font-size:22px;margin-bottom:8px}
.detalle{background:#f4f6f9;border-radius:8px;padding:14px;margin-top:20px;font-size:13px;color:#555;text-align:left}
.detalle b{color:#1a1a2e}
</style></head><body><div class="card">
<div class="ok">✅</div>
<h2>¡Documento enviado!</h2>
<p>Tu número de turno es:</p>
<div class="turno">#{{ turno }}</div>
<p style="color:#888;font-size:13px">Espera a que la encargada te llame</p>
<div class="detalle">
  <p><b>Nombre:</b> {{ nombre }}</p>
  <p style="margin-top:6px"><b>Archivo:</b> {{ archivo }}</p>
  <p style="margin-top:6px"><b>Hora:</b> {{ fecha }}</p>
  <p style="margin-top:6px"><b>Tamaño:</b> {{ tamano }}</p>
</div>
</div></body></html>"""

# ---------- rutas ----------

@app.route("/", methods=["GET","POST"])
def login():
    if session.get("auth"):
        return redirect("/panel")
    if request.method == "POST":
        if request.form.get("clave") == CLAVE:
            session["auth"] = True
            return redirect("/panel")
        return render_template_string(LOGIN, error=True)
    return render_template_string(LOGIN, error=False)

@app.route("/panel")
def panel():
    if not session.get("auth"):
        return redirect("/")
    host = request.host_url.rstrip("/")
    url_subida = host + "/subir"
    archivos_raw = sorted(os.listdir(CARPETA), reverse=True)
    archivos = []
    for nombre in archivos_raw:
        ruta = os.path.join(CARPETA, nombre)
        stat = os.stat(ruta)
        mb = stat.st_size / 1024 / 1024
        tamano = f"{mb:.2f} MB" if mb >= 1 else f"{stat.st_size//1024} KB"
        partes = nombre.split("_", 3)
        fecha_str = ""
        if len(partes) >= 2:
            try:
                fecha_str = datetime.strptime(partes[0]+"_"+partes[1], "%Y%m%d_%H%M%S").strftime("%d/%m/%Y %H:%M")
            except:
                fecha_str = ""
        archivos.append({"archivo": nombre, "nombre": nombre, "fecha": fecha_str, "tamano": tamano})
    historial = cargar_historial()
    return render_template_string(PANEL, qr=generar_qr(url_subida), url_subida=url_subida,
                                  archivos=archivos, total=len(archivos),
                                  historial=historial, hist_total=len(historial))

@app.route("/total")
def total():
    return {"total": len(os.listdir(CARPETA))}

@app.route("/subir", methods=["GET","POST"])
def subir():
    if request.method == "POST":
        f = request.files.get("doc")
        nombre = request.form.get("nombre","").strip() or "Estudiante"
        if not f or f.filename == "":
            return render_template_string(FORM)
        if not ext_ok(f.filename):
            return render_template_string(FORM)
        contenido = f.read()
        if len(contenido) > MAX_MB * 1024 * 1024:
            return render_template_string(FORM)
        turno = siguiente_turno() + 1
        fecha = datetime.now()
        fecha_str = fecha.strftime("%d/%m/%Y %H:%M")
        marca = fecha.strftime("%Y%m%d_%H%M%S")
        nombre_limpio = nombre.replace(" ","_")
        nombre_final = f"{marca}_{nombre_limpio}_{f.filename.replace(' ','_')}"
        ruta = os.path.join(CARPETA, nombre_final)
        with open(ruta, "wb") as out:
            out.write(contenido)
        mb = len(contenido) / 1024 / 1024
        tamano = f"{mb:.2f} MB" if mb >= 1 else f"{len(contenido)//1024} KB"
        h = cargar_historial()
        h.append({"turno": turno, "nombre": nombre, "archivo": f.filename, "fecha": fecha_str, "tamano": tamano})
        guardar_historial(h)
        return render_template_string(CONFIRMACION, turno=turno, nombre=nombre,
                                      archivo=f.filename, fecha=fecha_str, tamano=tamano)
    return render_template_string(FORM)

@app.route("/descargar/<nombre>")
def descargar(nombre):
    if not session.get("auth"):
        return redirect("/")
    ruta = os.path.join(CARPETA, nombre)
    if os.path.exists(ruta):
        return send_file(ruta, as_attachment=True)
    return "Archivo no encontrado.", 404

@app.route("/borrar/<nombre>", methods=["POST"])
def borrar(nombre):
    if not session.get("auth"):
        return redirect("/")
    ruta = os.path.join(CARPETA, nombre)
    if os.path.exists(ruta):
        os.remove(ruta)
    return redirect("/panel")

@app.route("/borrar-todos", methods=["POST"])
def borrar_todos():
    if not session.get("auth"):
        return redirect("/")
    for f in os.listdir(CARPETA):
        os.remove(os.path.join(CARPETA, f))
    return redirect("/panel")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
