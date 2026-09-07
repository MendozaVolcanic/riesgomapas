"""Tercera tanda del verificador: 118 (geolocalización denegada), 109 (enlaces
vacíos del catálogo) y 214/112 (sin red DE VERDAD: se apaga el servidor).
El servidor 8795 tiene que estar arriba al empezar; el script lo apaga solo.
"""
import socket, subprocess, sys, time
from playwright.sync_api import sync_playwright

BASE = "http://localhost:8795"


def servidor_vivo():
    s = socket.socket()
    s.settimeout(1)
    try:
        s.connect(("127.0.0.1", 8795)); return True
    except Exception:
        return False
    finally:
        s.close()


with sync_playwright() as pw:
    b = pw.chromium.launch()

    print("### 118 — geolocalización denegada")
    ctx = b.new_context(viewport={"width": 400, "height": 800})   # sin permiso
    page = ctx.new_page()
    page.goto(f"{BASE}/index.html", wait_until="networkidle")
    page.wait_for_function("() => !!window.estado && !!estado.puntos", timeout=30000)
    page.click("#btn-ubicacion")
    page.wait_for_timeout(3000)
    print("  #estado:", repr(page.inner_text("#estado").strip()))
    print("  idioma de la página:", page.evaluate("() => document.documentElement.lang"))

    print("\n### 109 — enlaces del catálogo con URL vacía")
    page.goto(f"{BASE}/documentos.html", wait_until="networkidle")
    page.wait_for_timeout(1500)
    r = page.evaluate("""() => {
      const as = [...document.querySelectorAll('a')];
      const vacios = as.filter(a => {
        const h = a.getAttribute('href');
        return h === '' || h === null || /^#page=/.test(h);
      });
      return {total: as.length, vacios: vacios.length,
              ejemplos: vacios.slice(0,4).map(a => [a.getAttribute('href'), a.innerText.trim().slice(0,40), a.href])};
    }""")
    print("  ", r)

    print("\n### 214/112 — sin red DE VERDAD (se apaga el servidor)")
    page.goto(f"{BASE}/index.html", wait_until="networkidle")
    page.wait_for_function("() => navigator.serviceWorker.controller !== null", timeout=20000)
    print("  service worker:", page.evaluate(
        "() => navigator.serviceWorker.controller ? 'activo' : 'sin controlador'"))
    # apagar el servidor
    subprocess.run(["powershell", "-NoProfile", "-Command",
                    "Get-NetTCPConnection -LocalPort 8795 -State Listen "
                    "| ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }"],
                   capture_output=True)
    for _ in range(20):
        if not servidor_vivo(): break
        time.sleep(0.5)
    print("  servidor apagado:", not servidor_vivo())
    for etq, u in [("PNG de plano (no precacheado)",
                    "data/planos/04_Anteproyecto-Planos_PRC_Vilcun_p001.png"),
                   ("índice de planos (precacheado)", "data/planos/indice.json"),
                   ("json inexistente", "data/no-existe.json"),
                   ("tesela Esri", "https://server.arcgisonline.com/ArcGIS/rest/services/"
                                   "World_Imagery/MapServer/tile/12/2400/1300")]:
        r = page.evaluate("""async (u) => {
          try { const r = await fetch(u); const t = await r.clone().text().catch(()=> '');
                return {ok: r.ok, status: r.status, tipo: r.headers.get('content-type'),
                        empieza: t.slice(0, 60)}; }
          catch (e) { return {error: String(e)}; }
        }""", u)
        print(f"  {etq} ->", r)

    print("\n  ¿qué pasa si se pide un plano estando sin red? (mostrarPlano)")
    r = page.evaluate("""async () => {
      const p = (estado.planos || [])[0];
      if (!p) return 'no hay planos';
      const antes = document.getElementById('estado').textContent;
      const ok = mostrarPlano(p);
      await new Promise(r => setTimeout(r, 1500));
      return {devolvio: ok, estado: document.getElementById('estado').textContent,
              capaEnMapa: !!estado.mapa.getLayer('plano-' + p.archivo.replace(/[^\\w]/g, ''))};
    }""")
    print("  ", r)
    b.close()
