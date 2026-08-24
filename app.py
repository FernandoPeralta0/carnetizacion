import os, io, base64, platform
from flask import Flask, request, render_template_string, send_file
from datetime import datetime
import qrcode

app = Flask(__name__)

CARPETA = "/tmp/documentos"
os.makedirs(CARPETA, exist_ok=True)

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

PANEL = """<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">
<meta http-equiv="refresh" content="10">
<title>Carnetización UTESA</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:Arial,sans-serif;background:#f0f2f5;padding:30px 16px;text-align:center}
.card{background:white;max-width:480px;margin:0 auto 24px;padding:28px;border-radius:16px;box-shadow:0 4px 16px rgba(0,0,0,.1)}
h1{color:#1a1a2e;margin-bottom:6px;font-size:22px}
p{color:#666;font-size:14px;margin-bottom:12px}
img.qr{width:230px;height:230px;margin:12px 0}
.url{font-size:11px;color:#aaa;word-break:break-all}
table{width:100%;border-collapse:collapse;font-size:13px;text-align:left}
th{background:#f4f4f4;padding:9px 12px;color:#333}
td{padding:9px 12px;border-bottom:1px solid #eee;vertical-align:middle}
.btn{display:inline-block;padding:6px 14px;background:#1a73e8;color:white;border-radius:6px;text-decoration:none;font-size:12px}
.btn-dl{background:#27ae60}
.empty{color:#999;padding:18px 0;font-size:14px}
</style></head><body>
<div class="card">
  <h1>📇 Carnetización UTESA</h1>
  <p>El estudiante escanea este QR desde su celular para enviar su documento</p>
  <img class="qr" src="data:image/png;base64,{{ qr }}">
  <p class="url">{{ url_subida }}</p>
</div>
<div class="card">
  <h1 style="font-size:17px;margin-bottom:16px">📂 Documentos recibidos</h1>
  {% if archivos %}
  <table>
    <tr><th>Estudiante / Archivo</th><th>Acción</th></tr>
    {% for a in archivos %}
    <tr>
      <td>{{ a }}</td>
      <td>
        <a class="btn btn-dl" href="/descargar/{{ a }}">⬇ Descargar</a>
      </td>
    </tr>
    {% endfor %}
  </table>
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
label{display:block;margin:16px 0 6px;font-size:14px;color:#444;font-weight:bold}
input{width:100%;padding:11px;border:1px solid #ccc;border-radius:8px;font-size:15px}
button{width:100%;margin-top:22px;padding:15px;background:#1a73e8;color:white;border:none;border-radius:8px;font-size:17px;cursor:pointer}
button:active{background:#1558b0}
.ok{background:#d4edda;color:#155724;padding:14px;border-radius:8px;text-align:center;margin-top:16px;font-size:15px}
.err{background:#f8d7da;color:#721c24;padding:14px;border-radius:8px;text-align:center;margin-top:16px;font-size:15px}
</style></head><body>
<div class="card">
  <h2>📄 Enviar documento a imprimir</h2>
  {% if msg %}<div class="{{ cls }}">{{ msg }}</div>{% endif %}
  <form method="post" enctype="multipart/form-data">
    <label>Tu nombre</label>
    <input type="text" name="nombre" placeholder="Ej. Juan Pérez" required>
    <label>Selecciona el documento</label>
    <input type="file" name="doc" accept=".pdf,.jpg,.jpeg,.png,.doc,.docx" required>
    <button type="submit">📤 Enviar documento</button>
  </form>
</div>
</body></html>"""

@app.route("/")
def panel():
    host = request.host_url.rstrip("/")
    url_subida = host + "/subir"
    archivos = sorted(os.listdir(CARPETA), reverse=True)[:20]
    return render_template_string(PANEL, qr=generar_qr(url_subida), url_subida=url_subida, archivos=archivos)

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
        return render_template_string(FORM, msg="✅ ¡Documento enviado con éxito! La encargada lo imprimirá en un momento.", cls="ok")
    return render_template_string(FORM, msg=None, cls="")

@app.route("/descargar/<nombre>")
def descargar(nombre):
    ruta = os.path.join(CARPETA, nombre)
    if os.path.exists(ruta):
        return send_file(ruta, as_attachment=True)
    return "Archivo no encontrado.", 404

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
