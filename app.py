import os, io, base64
from flask import Flask, request, render_template_string, send_file, redirect, session
from datetime import datetime
import qrcode

app = Flask(__name__)
app.secret_key = "utesa_2026"

CARPETA = "/tmp/documentos"
os.makedirs(CARPETA, exist_ok=True)

CLAVE = "carnet2024"  # <-- cambia esta contraseña

EXTS = {"pdf","jpg","jpeg","png","doc","docx"}

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
<meta http-equiv="refresh" content="15">
<title>Carnetización - Panel</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:Arial,sans-serif;background:#f0f2f5;padding:24px 16px;text-align:center}
.card{background:white;max-width:520px;margin:0 auto 20px;padding:28px;border-radius:16px;box-shadow:0 4px 16px rgba(0,0,0,.1)}
h1{color:#1a1a2e;margin-bottom:6px;font-size:21px}
p{color:#666;font-size:14px;margin-bottom:10px}
img.qr{width:220px;height:220px;margin:10px 0}
.url{font-size:11px;color:#aaa;word-break:break-all;margin-bottom:0}
table{width:100%;border-collapse:collapse;font-size:13px;text-align:left}
th{background:#f4f4f4;padding:9px 12px;color:#333}
td{padding:9px 12px;border-bottom:1px solid #eee;vertical-align:middle}
.btn{display:inline-block;padding:6px 13px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:600;border:none;cursor:pointer}
.btn-dl{background:#1a73e8;color:white}
.btn-del{background:#e74c3c;color:white}
.btn-logout{background:#555;color:white;font-size:13px;padding:8px 18px}
.empty{color:#999;padding:18px 0;font-size:14px}
.top{display:flex;justify-content:space-between;align-items:center;max-width:520px;margin:0 auto 14px}
</style></head><body>
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
  <h1 style="font-size:17px;margin-bottom:16px">📂 Documentos recibidos ({{ total }})</h1>
  {% if archivos %}
  <table>
    <tr><th>Archivo</th><th>Descargar</th><th>Borrar</th></tr>
    {% for a in archivos %}
    <tr>
      <td style="word-break:break-all;max-width:220px">{{ a }}</td>
      <td><a class="btn btn-dl" href="/descargar/{{ a }}">⬇ Descargar</a></td>
      <td>
        <form method="post" action="/borrar/{{ a }}" onsubmit="return confirm('¿Borrar este archivo?')">
          <button class="btn btn-del" type="submit">🗑 Borrar</button>
        </form>
      </td>
    </tr>
    {% endfor %}
  </table>
  {% if archivos|length > 1 %}
  <form method="post" action="/borrar-todos" onsubmit="return confirm('¿Borrar TODOS los documentos? Esta acción no se puede deshacer.')" style="margin-top:16px">
    <button class="btn btn-del" type="submit" style="width:100%;padding:10px;font-size:14px">🗑 Borrar todos los documentos</button>
  </form>
  {% endif %}
  {% else %}
  <p class="empty">Aún no se han recibido documentos.</p>
  {% endif %}
</div>
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
.ok{background:#d4edda;color:#155724;padding:14px;border-radius:8px;text-align:center;margin-top:16px;font-size:15px}
.err{background:#f8d7da;color:#721c24;padding:14px;border-radius:8px;text-align:center;margin-top:16px;font-size:15px}
</style></head><body><div class="card">
<h2>📄 Enviar documento a imprimir</h2>
{% if msg %}<div class="{{ cls }}">{{ msg }}</div>{% endif %}
<form method="post" enctype="multipart/form-data">
  <label>Tu nombre</label>
  <input type="text" name="nombre" placeholder="Ej. Juan Pérez" required>
  <label>Selecciona el documento</label>
  <input type="file" name="doc" accept=".pdf,.jpg,.jpeg,.png,.doc,.docx" required>
  <button type="submit">📤 Enviar documento</button>
</form>
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
    archivos = sorted(os.listdir(CARPETA), reverse=True)
    return render_template_string(PANEL, qr=generar_qr(url_subida), url_subida=url_subida, archivos=archivos, total=len(archivos))

@app.route("/subir", methods=["GET","POST"])
def subir():
    if request.method == "POST":
        f = request.files.get("doc")
        nombre = request.form.get("nombre","").strip().replace(" ","_") or "estudiante"
        if not f or f.filename == "":
            return render_template_string(FORM, msg="No seleccionaste ningún archivo.", cls="err")
        if not ext_ok(f.filename):
            return render_template_string(FORM, msg="Formato no permitido. Usa PDF, imagen JPG/PNG o Word.", cls="err")
        marca = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_final = f"{marca}_{nombre}_{f.filename.replace(' ','_')}"
        f.save(os.path.join(CARPETA, nombre_final))
        return render_template_string(FORM, msg="✅ ¡Documento enviado! La encargada lo imprimirá en un momento.", cls="ok")
    return render_template_string(FORM, msg=None, cls="")

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
