import os, io, base64, json, csv
from flask import Flask, request, render_template_string, send_file, redirect, session, Response
from datetime import datetime
import qrcode

app = Flask(__name__)
app.secret_key = "utesa_carnetizacion_2024"

CARPETA = "/tmp/documentos"
HISTORIAL_FILE = "/tmp/historial.json"
TURNO_FILE = "/tmp/turno.json"
ESTADO_FILE = "/tmp/estado.json"
os.makedirs(CARPETA, exist_ok=True)

CLAVE = "utesa2026"
EXTS = {"pdf","jpg","jpeg","png","doc","docx"}
MAX_MB = 25

def ext_ok(n):
    return "." in n and n.rsplit(".",1)[1].lower() in EXTS

def es_imagen(n):
    return "." in n and n.rsplit(".",1)[1].lower() in {"jpg","jpeg","png"}

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
    with open(HISTORIAL_FILE,"w") as f:
        json.dump(h, f, ensure_ascii=False)

def cargar_turno():
    if os.path.exists(TURNO_FILE):
        with open(TURNO_FILE) as f:
            return json.load(f).get("actual", 0)
    return 0

def siguiente_turno():
    actual = cargar_turno()
    nuevo = (actual % 50) + 1
    with open(TURNO_FILE,"w") as f:
        json.dump({"actual": nuevo}, f)
    return nuevo

def cargar_estado():
    if os.path.exists(ESTADO_FILE):
        with open(ESTADO_FILE) as f:
            return json.load(f)
    return {"turno_actual": 0, "atendidos_hoy": 0, "fecha_hoy": ""}

def guardar_estado(e):
    with open(ESTADO_FILE,"w") as f:
        json.dump(e, f, ensure_ascii=False)

def get_estado():
    e = cargar_estado()
    hoy = datetime.now().strftime("%Y-%m-%d")
    if e.get("fecha_hoy") != hoy:
        e["atendidos_hoy"] = 0
        e["fecha_hoy"] = hoy
        guardar_estado(e)
    return e

LOGIN = """<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Carnetización - Acceso</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:Arial,sans-serif;background:#f0f2f5;display:flex;align-items:center;justify-content:center;min-height:100vh;padding:20px}
.card{background:white;width:100%;max-width:380px;padding:32px;border-radius:16px;box-shadow:0 4px 16px rgba(0,0,0,.1);text-align:center}
h2{color:#1a1a2e;margin-bottom:8px;font-size:22px}p{color:#777;font-size:14px;margin-bottom:24px}
input{width:100%;padding:12px;border:1px solid #ccc;border-radius:8px;font-size:15px;margin-bottom:14px}
button{width:100%;padding:13px;background:#1a1a2e;color:white;border:none;border-radius:8px;font-size:16px;cursor:pointer}
.err{color:#c0392b;font-size:13px;margin-bottom:12px}
</style></head><body><div class="card">
<h2>📇 Carnetización UTESA</h2><p>Panel de la encargada</p>
{% if error %}<div class="err">Contraseña incorrecta.</div>{% endif %}
<form method="post">
  <input type="password" name="clave" placeholder="Contraseña" required>
  <button type="submit">Entrar</button>
</form></div></body></html>"""

PANEL = """<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">
<title>Carnetización - Panel</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:Arial,sans-serif;background:#f0f2f5;padding:20px 16px}
.wrap{max-width:680px;margin:0 auto}
.top{display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;flex-wrap:wrap;gap:8px}
.card{background:white;padding:24px;border-radius:16px;box-shadow:0 4px 16px rgba(0,0,0,.1);margin-bottom:18px;text-align:center}
h1{color:#1a1a2e;font-size:20px;margin-bottom:6px}
p{color:#666;font-size:13px;margin-bottom:8px}
img.qr{width:180px;height:180px;margin:8px 0}
.url{font-size:11px;color:#aaa;word-break:break-all}
.stats{display:flex;gap:12px;margin-bottom:18px}
.stat{flex:1;background:white;border-radius:12px;padding:14px;text-align:center;box-shadow:0 4px 16px rgba(0,0,0,.08)}
.stat-num{font-size:28px;font-weight:700;color:#1a1a2e}
.stat-label{font-size:11px;color:#888;margin-top:4px}
.tabs{display:flex;gap:8px;margin-bottom:14px}
.tab{flex:1;padding:9px;border-radius:8px;border:2px solid #ddd;cursor:pointer;font-size:13px;background:white;color:#555;font-weight:600}
.tab.active{background:#1a1a2e;color:white;border-color:#1a1a2e}
.section{display:none}.section.active{display:block}
table{width:100%;border-collapse:collapse;font-size:12px;text-align:left}
th{background:#f4f4f4;padding:8px 8px;color:#333}
td{padding:8px 8px;border-bottom:1px solid #eee;vertical-align:middle}
.btn{display:inline-block;padding:5px 10px;border-radius:6px;text-decoration:none;font-size:11px;font-weight:600;border:none;cursor:pointer;white-space:nowrap}
.bl{background:#1a1a2e;color:white}
.bg{background:#27ae60;color:white}
.br{background:#e74c3c;color:white}
.bo{background:#e67e22;color:white}
.bb{background:#1a73e8;color:white}
.bpurple{background:#8e44ad;color:white}
.btn-logout{background:#555;color:white;font-size:12px;padding:7px 14px;border-radius:6px;text-decoration:none}
.badge{display:inline-block;background:#1a1a2e;color:white;border-radius:50%;width:26px;height:26px;line-height:26px;text-align:center;font-weight:700;font-size:11px}
.badge-g{background:#27ae60}
.empty{color:#999;padding:16px 0;font-size:14px;text-align:center}
.nuevo{background:#fff8e1}
.btn-full{width:100%;padding:10px;font-size:13px;margin-top:8px}
.buscar{width:100%;padding:9px 12px;border:1px solid #ddd;border-radius:8px;font-size:13px;margin-bottom:12px;box-sizing:border-box}
.preview-thumb{width:40px;height:40px;object-fit:cover;border-radius:4px;cursor:pointer;border:1px solid #eee}
.modal{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.8);z-index:999;align-items:center;justify-content:center}
.modal.open{display:flex}
.modal img{max-width:90%;max-height:90vh;border-radius:8px}
.modal-close{position:absolute;top:20px;right:28px;color:white;font-size:32px;cursor:pointer;font-weight:700}
</style>
<audio id="alerta" src="https://www.soundjay.com/buttons/sounds/button-09.mp3" preload="auto"></audio>
</head><body><div class="wrap">

<div id="modal" class="modal" onclick="cerrarModal()">
  <span class="modal-close">✕</span>
  <img id="modal-img" src="" alt="Vista previa">
</div>

<div class="top">
  <span style="font-size:13px;color:#555">Bienvenida 👋</span>
  <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
    <a href="/pantalla" target="_blank" class="btn bpurple">📺 Pantalla turnos</a>
    <a href="/exportar" class="btn bg">📥 Exportar Excel</a>
    <a href="/logout" class="btn-logout">Cerrar sesión</a>
  </div>
</div>

<div class="stats">
  <div class="stat"><div class="stat-num">{{ total }}</div><div class="stat-label">Pendientes</div></div>
  <div class="stat"><div class="stat-num" style="color:#27ae60">{{ atendidos_hoy }}</div><div class="stat-label">Atendidos hoy</div></div>
  <div class="stat"><div class="stat-num" style="color:#8e44ad">{% if turno_actual > 0 %}#{{ turno_actual }}{% else %}—{% endif %}</div><div class="stat-label">Turno en pantalla</div></div>
</div>

<div class="card">
  <h1>📇 Carnetización UTESA</h1>
  <p>Los estudiantes escanean este QR para enviar documentos</p>
  <img class="qr" src="data:image/png;base64,{{ qr }}">
  <p class="url">{{ url_subida }}</p>
</div>

<div class="card" style="text-align:left">
  <div class="tabs">
    <button class="tab active" onclick="mostrar('pendientes',this)">📂 Pendientes ({{ total }})</button>
    <button class="tab" onclick="mostrar('historial',this)">✅ Historial ({{ hist_total }})</button>
  </div>

  <div id="pendientes" class="section active">
    {% if archivos %}
    <table>
      <tr><th>#</th><th>Preview</th><th>Nombre</th><th>Hora</th><th>Tam.</th><th colspan="3">Acciones</th></tr>
      {% for a in archivos %}
      <tr class="{{ 'nuevo' if loop.first else '' }}">
        <td><span class="badge">{{ a.turno }}</span></td>
        <td>
          {% if a.es_imagen %}
          <img class="preview-thumb" src="/preview/{{ a.archivo }}" onclick="abrirModal('/preview/{{ a.archivo }}')" alt="preview">
          {% else %}
          <span style="font-size:20px">📄</span>
          {% endif %}
        </td>
        <td style="word-break:break-all;max-width:120px">{{ a.nombre_estudiante }}</td>
        <td style="white-space:nowrap">{{ a.hora }}</td>
        <td>{{ a.tamano }}</td>
        <td>
          <form method="post" action="/llamar/{{ a.turno }}" style="display:inline">
            <button class="btn bpurple">📺 Llamar</button>
          </form>
        </td>
        <td>
          <form method="post" action="/atender/{{ a.archivo }}" style="display:inline" onsubmit="return confirm('¿Marcar como atendido?')">
            <button class="btn bg">✓ Atendido</button>
          </form>
        </td>
        <td><a class="btn bb" href="/descargar/{{ a.archivo }}">⬇</a></td>
      </tr>
      {% endfor %}
    </table>
    <form method="post" action="/borrar-todos" onsubmit="return confirm('¿Borrar TODOS los pendientes?')" style="margin-top:10px">
      <button class="btn br btn-full">🗑 Borrar todos los pendientes</button>
    </form>
    <form method="post" action="/reiniciar-turno" onsubmit="return confirm('¿Reiniciar turnos desde #1?')" style="margin-top:8px">
      <button class="btn bo btn-full">🔄 Reiniciar turnos desde #1</button>
    </form>
    {% else %}
    <p class="empty">No hay documentos pendientes.</p>
    <form method="post" action="/reiniciar-turno" onsubmit="return confirm('¿Reiniciar turnos desde #1?')" style="margin-top:8px">
      <button class="btn bo btn-full">🔄 Reiniciar turnos desde #1</button>
    </form>
    {% endif %}
  </div>

  <div id="historial" class="section">
    <input class="buscar" type="text" id="buscar" placeholder="🔍 Buscar por nombre, fecha o turno..." oninput="filtrarHistorial()">
    {% if historial %}
    <table id="tabla-historial">
      <tr><th>#</th><th>Nombre</th><th>Fecha y hora</th><th>Tamaño</th><th>Estado</th></tr>
      {% for h in historial|reverse %}
      <tr class="fila-hist">
        <td><span class="badge badge-g">{{ h.turno }}</span></td>
        <td style="word-break:break-all;max-width:180px">{{ h.nombre }}</td>
        <td style="white-space:nowrap">{{ h.fecha }}</td>
        <td>{{ h.tamano }}</td>
        <td style="color:#27ae60;font-weight:600">✓ Atendido</td>
      </tr>
      {% endfor %}
    </table>
    {% else %}
    <p class="empty">El historial está vacío.</p>
    {% endif %}
  </div>
</div>
</div>

<script>
function mostrar(id,btn){
  document.querySelectorAll('.section').forEach(s=>s.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  document.getElementById(id).classList.add('active');
  btn.classList.add('active');
}
function abrirModal(src){
  document.getElementById('modal-img').src=src;
  document.getElementById('modal').classList.add('open');
}
function cerrarModal(){
  document.getElementById('modal').classList.remove('open');
}
function filtrarHistorial(){
  var q=document.getElementById('buscar').value.toLowerCase();
  document.querySelectorAll('.fila-hist').forEach(function(row){
    row.style.display=row.textContent.toLowerCase().includes(q)?'':'none';
  });
}
var totalAnterior={{ total }};
setInterval(function(){
  fetch('/total').then(r=>r.json()).then(d=>{
    if(d.total>totalAnterior){
      document.getElementById('alerta').play();
      totalAnterior=d.total;
      location.reload();
    }
  });
},5000);
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
.preview-box{margin-top:12px;text-align:center;display:none}
.preview-box img{max-width:100%;max-height:200px;border-radius:8px;border:1px solid #eee}
.preview-box .nombre-archivo{font-size:12px;color:#666;margin-top:6px}
</style></head><body><div class="card">
<h2>📄 Enviar documento a imprimir</h2>
<form method="post" enctype="multipart/form-data" onsubmit="return validar()">
  <label>Tu nombre</label>
  <input type="text" name="nombre" placeholder="Ej. Juan Pérez" required>
  <label>Selecciona el documento</label>
  <input type="file" name="doc" id="doc" accept=".pdf,.jpg,.jpeg,.png,.doc,.docx" required onchange="mostrarPreview()">
  <div class="info">Formatos: PDF, Word, JPG, PNG &nbsp;•&nbsp; Máximo: 25 MB</div>
  <div id="peso" class="info" style="color:#1a73e8;margin-top:4px"></div>
  <div id="err-size" class="err-size">⚠ El archivo supera los 25 MB.</div>
  <div class="preview-box" id="preview-box">
    <img id="preview-img" src="" alt="Vista previa">
    <div class="nombre-archivo" id="nombre-archivo"></div>
  </div>
  <button type="submit">📤 Enviar documento</button>
</form></div>
<script>
function mostrarPreview(){
  var f=document.getElementById('doc').files[0];
  var err=document.getElementById('err-size');
  var info=document.getElementById('peso');
  var box=document.getElementById('preview-box');
  var img=document.getElementById('preview-img');
  var nombre=document.getElementById('nombre-archivo');
  if(f){
    var mb=(f.size/1024/1024).toFixed(2);
    info.textContent='Tamaño: '+mb+' MB';
    err.style.display=f.size>25*1024*1024?'block':'none';
    nombre.textContent=f.name;
    if(f.type.startsWith('image/')){
      var reader=new FileReader();
      reader.onload=function(e){img.src=e.target.result;box.style.display='block';};
      reader.readAsDataURL(f);
    } else {
      img.src='';
      box.style.display='block';
      img.style.display='none';
    }
  }
}
function validar(){
  var f=document.getElementById('doc').files[0];
  if(f&&f.size>25*1024*1024){document.getElementById('err-size').style.display='block';return false;}
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
.turno{font-size:90px;font-weight:700;color:#1a1a2e;line-height:1;margin:16px 0}
h2{color:#1a1a2e;font-size:20px;margin-bottom:8px}
p{color:#666;font-size:15px;margin-bottom:6px}
.ok{color:#27ae60;font-size:26px;margin-bottom:8px}
.detalle{background:#f4f6f9;border-radius:8px;padding:14px;margin-top:20px;font-size:13px;color:#555;text-align:left;line-height:2}
.detalle b{color:#1a1a2e}
</style></head><body><div class="card">
<div class="ok">✅</div>
<h2>¡Documento enviado!</h2>
<p>Tu número de turno es:</p>
<div class="turno">#{{ turno }}</div>
<p style="color:#888;font-size:13px">Espera a que te llamen</p>
<div class="detalle">
  <div><b>Nombre:</b> {{ nombre }}</div>
  <div><b>Archivo:</b> {{ archivo }}</div>
  <div><b>Hora:</b> {{ fecha }}</div>
  <div><b>Tamaño:</b> {{ tamano }}</div>
</div>
</div></body></html>"""

PANTALLA = """<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">
<title>Turnos - Carnetización</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:Arial,sans-serif;background:#1a1a2e;display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:100vh;text-align:center;padding:20px}
h1{color:white;font-size:26px;margin-bottom:6px;opacity:0.7}
.sub{color:#aaa;font-size:15px;margin-bottom:36px}
.turno-box{background:white;border-radius:24px;padding:36px 56px;margin-bottom:28px}
.label{color:#888;font-size:17px;margin-bottom:8px}
.numero{font-size:150px;font-weight:700;color:#1a1a2e;line-height:1}
.esperando{color:#aaa;font-size:20px;margin-top:10px}
.atendidos{background:rgba(255,255,255,0.1);border-radius:12px;padding:14px 30px;color:white}
.at-num{font-size:44px;font-weight:700;color:#27ae60}
.at-label{font-size:13px;color:#aaa;margin-top:4px}
</style></head><body>
<h1>📇 Carnetización UTESA</h1>
<p class="sub">Pantalla de turnos</p>
<div class="turno-box">
  <div class="label">Turno en atención</div>
  {% if turno > 0 %}<div class="numero">#{{ turno }}</div>
  {% else %}<div class="esperando">Esperando...</div>{% endif %}
</div>
<div class="atendidos">
  <div class="at-num">{{ atendidos }}</div>
  <div class="at-label">Atendidos hoy</div>
</div>
<script>setInterval(function(){location.reload();},4000);</script>
</body></html>"""

# ─── RUTAS ───────────────────────────────────────────────────

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
        mb = stat.st_size/1024/1024
        tamano = f"{mb:.2f} MB" if mb>=1 else f"{stat.st_size//1024} KB"
        partes = nombre.split("_")
        hora = ""
        turno_num = "?"
        nombre_est = nombre
        try:
            hora = datetime.strptime(partes[0]+"_"+partes[1], "%Y%m%d_%H%M%S").strftime("%H:%M")
            turno_num = partes[2]
            nombre_est = partes[3].replace("_"," ") if len(partes)>3 else nombre
        except:
            pass
        archivos.append({"archivo":nombre,"nombre_estudiante":nombre_est,"hora":hora,
                         "tamano":tamano,"turno":turno_num,"es_imagen":es_imagen(nombre)})
    historial = cargar_historial()
    e = get_estado()
    return render_template_string(PANEL, qr=generar_qr(url_subida), url_subida=url_subida,
                                  archivos=archivos, total=len(archivos),
                                  historial=historial, hist_total=len(historial),
                                  atendidos_hoy=e["atendidos_hoy"],
                                  turno_actual=e.get("turno_actual",0))

@app.route("/total")
def total():
    return {"total": len(os.listdir(CARPETA))}

@app.route("/preview/<nombre>")
def preview(nombre):
    if not session.get("auth"):
        return redirect("/")
    ruta = os.path.join(CARPETA, nombre)
    if os.path.exists(ruta) and es_imagen(nombre):
        return send_file(ruta)
    return "No disponible", 404

@app.route("/subir", methods=["GET","POST"])
def subir():
    if request.method == "POST":
        f = request.files.get("doc")
        nombre = request.form.get("nombre","").strip() or "Estudiante"
        if not f or f.filename == "" or not ext_ok(f.filename):
            return render_template_string(FORM)
        contenido = f.read()
        if len(contenido) > MAX_MB*1024*1024:
            return render_template_string(FORM)
        turno = siguiente_turno()
        fecha = datetime.now()
        fecha_str = fecha.strftime("%d/%m/%Y %H:%M")
        marca = fecha.strftime("%Y%m%d_%H%M%S")
        nombre_limpio = nombre.replace(" ","_")
        nombre_final = f"{marca}_{turno}_{nombre_limpio}_{f.filename.replace(' ','_')}"
        with open(os.path.join(CARPETA, nombre_final),"wb") as out:
            out.write(contenido)
        mb = len(contenido)/1024/1024
        tamano = f"{mb:.2f} MB" if mb>=1 else f"{len(contenido)//1024} KB"
        return render_template_string(CONFIRMACION, turno=turno, nombre=nombre,
                                      archivo=f.filename, fecha=fecha_str, tamano=tamano)
    return render_template_string(FORM)

@app.route("/exportar")
def exportar():
    if not session.get("auth"):
        return redirect("/")
    historial = cargar_historial()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Turno","Nombre","Fecha y hora","Tamaño","Estado"])
    for h in historial:
        writer.writerow([h.get("turno",""), h.get("nombre",""), h.get("fecha",""), h.get("tamano",""), "Atendido"])
    output.seek(0)
    fecha_hoy = datetime.now().strftime("%Y%m%d")
    return Response(output.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": f"attachment;filename=historial_{fecha_hoy}.csv"})

@app.route("/llamar/<int:turno>", methods=["POST"])
def llamar(turno):
    if not session.get("auth"):
        return redirect("/")
    e = get_estado()
    e["turno_actual"] = turno
    guardar_estado(e)
    return redirect("/panel")

@app.route("/atender/<nombre>", methods=["POST"])
def atender(nombre):
    if not session.get("auth"):
        return redirect("/")
    ruta = os.path.join(CARPETA, nombre)
    if os.path.exists(ruta):
        partes = nombre.split("_")
        turno_num = int(partes[2]) if len(partes)>2 and partes[2].isdigit() else 0
        nombre_est = partes[3].replace("_"," ") if len(partes)>3 else nombre
        hora = ""
        try:
            hora = datetime.strptime(partes[0]+"_"+partes[1], "%Y%m%d_%H%M%S").strftime("%d/%m/%Y %H:%M")
        except:
            hora = datetime.now().strftime("%d/%m/%Y %H:%M")
        stat = os.stat(ruta)
        mb = stat.st_size/1024/1024
        tamano = f"{mb:.2f} MB" if mb>=1 else f"{stat.st_size//1024} KB"
        h = cargar_historial()
        h.append({"turno":turno_num,"nombre":nombre_est,"archivo":nombre,"fecha":hora,"tamano":tamano})
        guardar_historial(h)
        e = get_estado()
        e["atendidos_hoy"] = e.get("atendidos_hoy",0) + 1
        guardar_estado(e)
        os.remove(ruta)
    return redirect("/panel")

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

@app.route("/reiniciar-turno", methods=["POST"])
def reiniciar_turno():
    if not session.get("auth"):
        return redirect("/")
    with open(TURNO_FILE,"w") as f:
        json.dump({"actual":0}, f)
    return redirect("/panel")

@app.route("/pantalla")
def pantalla():
    e = get_estado()
    return render_template_string(PANTALLA, turno=e.get("turno_actual",0), atendidos=e.get("atendidos_hoy",0))

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    port = int(os.environ.get("PORT",5000))
    app.run(host="0.0.0.0", port=port)
