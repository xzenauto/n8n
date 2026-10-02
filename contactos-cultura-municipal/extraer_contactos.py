#!/usr/bin/env python3
"""
Directorio nacional de contactos de cultura municipal (México).

Descarga los datos abiertos del Sistema de Información Cultural (SIC) de la
Secretaría de Cultura federal y genera un CSV consolidado con nombre de la
institución, titular (cuando está disponible), teléfono y correo de las
áreas municipales de cultura de todo el país.

Fuentes (datos públicos):
  https://sic.cultura.gob.mx/opendata/d/0_institucion_cultural_mun_directorio.csv
      -> institutos / direcciones / coordinaciones municipales de cultura
  https://sic.cultura.gob.mx/opendata/d/0_centro_cultural_directorio.csv
      -> casas de cultura y centros culturales (muchos son municipales)
  https://sic.cultura.gob.mx/opendata/d/0_festival_directorio.csv
      -> festivales y ferias culturales (organizadores)

Uso:
  python3 extraer_contactos.py                 # descarga y consolida
  python3 extraer_contactos.py --fichas        # además visita cada ficha del SIC
                                               # para sacar el nombre del titular
  python3 extraer_contactos.py --local carpeta # usa CSV ya descargados

Sólo usa la biblioteca estándar de Python 3.8+.
"""

import argparse
import csv
import html
import io
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.request

BASE = "https://sic.cultura.gob.mx/opendata/d/{clave}_{tabla}_directorio.csv"

TABLAS = {
    "institucion_cultural_mun": "Instituto/Dirección municipal de cultura",
    "centro_cultural": "Casa de cultura / Centro cultural",
    "festival": "Festival / Feria cultural",
}

ESTADOS = {
    1: "Aguascalientes", 2: "Baja California", 3: "Baja California Sur",
    4: "Campeche", 5: "Coahuila", 6: "Colima", 7: "Chiapas", 8: "Chihuahua",
    9: "Ciudad de México", 10: "Durango", 11: "Guanajuato", 12: "Guerrero",
    13: "Hidalgo", 14: "Jalisco", 15: "México", 16: "Michoacán", 17: "Morelos",
    18: "Nayarit", 19: "Nuevo León", 20: "Oaxaca", 21: "Puebla",
    22: "Querétaro", 23: "Quintana Roo", 24: "San Luis Potosí", 25: "Sinaloa",
    26: "Sonora", 27: "Tabasco", 28: "Tamaulipas", 29: "Tlaxcala",
    30: "Veracruz", 31: "Yucatán", 32: "Zacatecas",
}

UA = "Mozilla/5.0 (directorio-cultura-municipal; datos abiertos SIC)"

COLUMNAS_SALIDA = [
    "estado", "municipio", "tipo", "nivel", "institucion", "adscripcion",
    "titular", "cargo_titular", "telefono", "correo", "correo_institucional",
    "pagina_web", "domicilio", "organizador_festival", "fecha_festival",
    "ficha_sic", "ultima_actualizacion",
]

RE_EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
DOMINIOS_PERSONALES = (
    "gmail.", "hotmail.", "yahoo.", "outlook.", "live.", "icloud.",
    "prodigy.net", "aol.", "msn.",
)


def normaliza(texto):
    texto = unicodedata.normalize("NFKD", str(texto or ""))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "_", texto.lower()).strip("_")


def descargar(url, reintentos=4):
    espera = 2
    for intento in range(reintentos):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            error = e
        except Exception as e:  # red, timeout
            error = e
        if intento < reintentos - 1:
            time.sleep(espera)
            espera *= 2
    print(f"  ! no se pudo descargar {url}: {error}", file=sys.stderr)
    return None


def decodificar(datos):
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return datos.decode(enc)
        except UnicodeDecodeError:
            continue
    return datos.decode("utf-8", errors="replace")


def leer_csv(texto):
    muestra = texto[:5000]
    try:
        dialecto = csv.Sniffer().sniff(muestra, delimiters=",;|\t")
    except csv.Error:
        dialecto = csv.excel
    lector = csv.DictReader(io.StringIO(texto), dialect=dialecto)
    return [{normaliza(k): (v or "").strip() for k, v in fila.items() if k} for fila in lector]


def campo(fila, *claves, contiene=()):
    """Devuelve el primer valor no vacío cuyo nombre de columna coincida."""
    for c in claves:
        if fila.get(c):
            return fila[c]
    for patron in contiene:
        for k, v in fila.items():
            if patron in k and v:
                return v
    return ""


def limpia_telefono(tel):
    tel = re.sub(r"\s+", " ", tel).strip(" ,;")
    return "" if not re.search(r"\d{7,}", re.sub(r"[^\d]", "", tel)) else tel


def correos(texto):
    vistos = []
    for c in RE_EMAIL.findall(texto or ""):
        c = c.lower().rstrip(".")
        if c not in vistos:
            vistos.append(c)
    return vistos


def es_institucional(correo):
    return bool(correo) and not any(d in correo for d in DOMINIOS_PERSONALES)


def nivel_gobierno(adscripcion, nombre, tipo):
    t = normaliza(f"{adscripcion} {nombre}")
    if tipo == "institucion_cultural_mun":
        return "Municipal"
    if re.search(r"municip|ayuntamiento|alcaldia|delegacion|h_ayto|cabildo", t):
        return "Municipal"
    if re.search(r"particular|privad|asociacion_civil|a_c$|_a_c_|fundacion", t):
        return "Privado / A.C."
    if re.search(r"issste|imss|inah|inba|suprema_corte|federal|secretaria_de_cultura$|"
                 r"cdi|inpi|conaculta|universidad|unam|ipn", t):
        return "Federal / Otro"
    if re.search(r"estatal|estado|gobierno_de|instituto_.*cultur|consejo|secretaria_de_cultura", t):
        return "Estatal"
    return "Sin dato"


def a_registro(fila, tipo):
    estado = campo(fila, "nom_ent", "estado", "entidad")
    municipio = campo(fila, "nom_mun", "municipio")
    if normaliza(estado) == "total_nacional":
        estado = ""
    if normaliza(municipio) == "total_nacional":
        municipio = ""
    nombre = campo(fila, f"{tipo}_nombre", "nombre", contiene=("_nombre",))
    adscripcion = campo(fila, f"{tipo}_adscripcion", "adscripcion", contiene=("adscripcion",))
    titular = campo(fila, "titular", "director", "responsable")
    tels = [limpia_telefono(v) for k, v in fila.items()
            if re.search(r"tel(e)?fono|telfono", k) and v]
    tel = "; ".join(t for t in tels if t)
    texto_correo = " ".join(v for k, v in fila.items() if "mail" in k or "correo" in k)
    lista_correos = correos(texto_correo)
    calle = campo(fila, f"{tipo}_calle_numero", "calle_numero", contiene=("calle",))
    colonia = campo(fila, f"{tipo}_colonia", contiene=("colonia",))
    cp = campo(fila, f"{tipo}_cp", "codigo_postal")
    domicilio = ", ".join(p for p in (calle, colonia, f"C.P. {cp}" if cp else "") if p)
    ficha = campo(fila, "link_sic", contiene=("link",))
    ficha = ficha.replace("http://sic.gob.mx/", "https://sic.cultura.gob.mx/")
    return {
        "estado": estado,
        "municipio": municipio,
        "tipo": TABLAS[tipo],
        "nivel": nivel_gobierno(adscripcion, nombre, tipo),
        "institucion": nombre,
        "adscripcion": adscripcion,
        "titular": titular,
        "cargo_titular": "",
        "telefono": tel,
        "correo": "; ".join(lista_correos),
        "correo_institucional": "sí" if any(es_institucional(c) for c in lista_correos) else "no",
        "pagina_web": campo(fila, "pagina_web", "pagina_web2", contiene=("pagina_web",)),
        "domicilio": domicilio,
        "organizador_festival": "",
        "fecha_festival": "",
        "ficha_sic": ficha,
        "ultima_actualizacion": campo(fila, "fecha_mod")[:10],
    }


# --- Ficha individual del SIC: titular / director -----------------------------

def texto_plano(pagina):
    pagina = re.sub(r"(?is)<(script|style).*?</\1>", " ", pagina)
    pagina = re.sub(r"<[^>]+>", "\n", pagina)
    lineas = [re.sub(r"\s+", " ", html.unescape(l)).strip() for l in pagina.split("\n")]
    return [l for l in lineas if l]


ETIQUETAS = {"datos generales", "sede", "otras sedes", "fecha", "institucion organizadora",
             "institucion coadyuvante", "responsable", "abrir en google maps"}


def datos_de_ficha(url):
    """Extrae del bloque principal de la ficha: responsable, cargo, teléfonos,
    correos, municipio/estado (línea 'CP ..., Municipio, Estado') y, en
    festivales, institución organizadora y fecha."""
    datos = descargar(url, reintentos=3)
    if not datos:
        return None
    lineas = texto_plano(decodificar(datos))
    try:
        ini = max(i for i, l in enumerate(lineas) if l == "Interruptor de Navegación")
    except ValueError:
        ini = 0
    fin = next((i for i in range(ini, len(lineas)) if lineas[i].startswith("¿Detectaste")), len(lineas))
    bloque = lineas[ini:fin]
    r = {"titular": "", "cargo": "", "telefono": "", "correos": [], "municipio": "",
         "estado": "", "organizador": "", "fecha": ""}

    def siguiente(i):
        return bloque[i + 1] if i + 1 < len(bloque) else ""

    for i, l in enumerate(bloque):
        ln = normaliza(l)
        if l.startswith("Tels.") or l.startswith("Tel."):
            r["telefono"] = l.split(":", 1)[-1].strip()
        elif re.match(r"CP \d{4,5},", l):
            partes = [p.strip() for p in l.split(",")]
            if len(partes) >= 3:
                r["municipio"], r["estado"] = partes[-2], partes[-1]
        elif ln == "responsable":
            nombre = siguiente(i)
            if nombre and normaliza(nombre) not in ETIQUETAS and not RE_EMAIL.search(nombre):
                r["titular"] = nombre
                cargo = bloque[i + 2] if i + 2 < len(bloque) else ""
                if cargo and re.match(r"[A-Za-zÁÉÍÓÚÑáéíóúñ]", cargo) \
                        and normaliza(cargo).replace("_", " ") not in ETIQUETAS \
                        and len(cargo) < 120 and not RE_EMAIL.search(cargo):
                    r["cargo"] = cargo
        elif ln == "institucion_organizadora":
            r["organizador"] = siguiente(i)
        elif ln == "fecha":
            r["fecha"] = siguiente(i)
        r["correos"] += [c for c in correos(l) if c not in r["correos"]]
    return r


# --- Programa principal -------------------------------------------------------

def obtener_filas(tabla, carpeta_local, carpeta_crudos):
    nombre = f"0_{tabla}_directorio.csv"
    if carpeta_local:
        ruta = os.path.join(carpeta_local, nombre)
        if os.path.exists(ruta):
            with open(ruta, "rb") as f:
                return leer_csv(decodificar(f.read()))
    datos = descargar(BASE.format(clave=0, tabla=tabla))
    if datos:
        with open(os.path.join(carpeta_crudos, nombre), "wb") as f:
            f.write(datos)
        return leer_csv(decodificar(datos))
    # Si el nacional no existe, se arma con los 32 estatales.
    filas = []
    for clave, estado in ESTADOS.items():
        datos = descargar(BASE.format(clave=clave, tabla=tabla))
        if not datos:
            continue
        with open(os.path.join(carpeta_crudos, f"{clave}_{tabla}_directorio.csv"), "wb") as f:
            f.write(datos)
        for fila in leer_csv(decodificar(datos)):
            fila.setdefault("estado", estado)
            filas.append(fila)
    return filas


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--salida", default="directorio_cultura_municipal.csv")
    ap.add_argument("--local", help="carpeta con CSV del SIC ya descargados")
    ap.add_argument("--tablas", default=",".join(TABLAS), help="tablas del SIC a incluir")
    ap.add_argument("--fichas", action="store_true",
                    help="visita la ficha de cada registro para extraer el titular (lento)")
    ap.add_argument("--pausa", type=float, default=0.3, help="segundos de pausa por ficha y por hilo")
    ap.add_argument("--hilos", type=int, default=6, help="fichas consultadas en paralelo")
    ap.add_argument("--solo-municipal", action="store_true",
                    help="excluye registros estatales, federales y privados")
    ap.add_argument("--solo-con-contacto", action="store_true",
                    help="descarta registros sin teléfono ni correo")
    args = ap.parse_args()

    carpeta = os.path.dirname(os.path.abspath(args.salida))
    crudos = os.path.join(carpeta, "crudos_sic")
    os.makedirs(crudos, exist_ok=True)

    registros = []
    for tabla in [t.strip() for t in args.tablas.split(",") if t.strip()]:
        if tabla not in TABLAS:
            print(f"  ! tabla desconocida: {tabla}", file=sys.stderr)
            continue
        filas = obtener_filas(tabla, args.local, crudos)
        print(f"{tabla}: {len(filas)} registros")
        registros.extend(a_registro(f, tabla) for f in filas)

    if args.fichas:
        from concurrent.futures import ThreadPoolExecutor
        pendientes = [r for r in registros if r["ficha_sic"]]
        print(f"Consultando {len(pendientes)} fichas del SIC...")

        def procesa(r):
            time.sleep(args.pausa)
            return r, datos_de_ficha(r["ficha_sic"])

        with ThreadPoolExecutor(max_workers=args.hilos) as ex:
            for i, (r, d) in enumerate(ex.map(procesa, pendientes), 1):
                if d:
                    r["titular"] = r["titular"] or d["titular"]
                    r["cargo_titular"] = d["cargo"]
                    if d["telefono"] and not r["telefono"]:
                        r["telefono"] = d["telefono"]
                    r["estado"] = r["estado"] or d["estado"]
                    r["municipio"] = r["municipio"] or d["municipio"]
                    r["organizador_festival"] = d["organizador"]
                    r["fecha_festival"] = d["fecha"]
                    todos = correos(r["correo"])
                    todos += [c for c in d["correos"] if c not in todos]
                    r["correo"] = "; ".join(todos)
                    r["correo_institucional"] = "sí" if any(es_institucional(c) for c in todos) else "no"
                if i % 250 == 0:
                    print(f"  {i}/{len(pendientes)}", flush=True)

    if args.solo_municipal:
        registros = [r for r in registros if r["nivel"] in ("Municipal", "Sin dato")
                     or r["tipo"] == TABLAS["festival"]]
    if args.solo_con_contacto:
        registros = [r for r in registros if r["telefono"] or r["correo"]]

    # Quitar duplicados exactos (misma institución, municipio y correo/teléfono).
    unicos, vistos = [], set()
    for r in registros:
        clave = (normaliza(r["estado"]), normaliza(r["municipio"]),
                 normaliza(r["institucion"]), r["correo"], r["telefono"])
        if clave not in vistos:
            vistos.add(clave)
            unicos.append(r)
    unicos.sort(key=lambda r: (normaliza(r["estado"]), normaliza(r["municipio"]), r["tipo"]))

    with open(args.salida, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNAS_SALIDA)
        w.writeheader()
        w.writerows(unicos)

    con_correo = sum(1 for r in unicos if r["correo"])
    con_tel = sum(1 for r in unicos if r["telefono"])
    con_titular = sum(1 for r in unicos if r["titular"])
    municipios = len({(normaliza(r["estado"]), normaliza(r["municipio"])) for r in unicos})
    print(f"\n{len(unicos)} registros -> {args.salida}")
    print(f"  municipios cubiertos: {municipios}")
    print(f"  con correo: {con_correo} | con teléfono: {con_tel} | con titular: {con_titular}")

    resumen = os.path.join(carpeta, "resumen_por_estado.csv")
    por_estado = {}
    for r in unicos:
        e = por_estado.setdefault(r["estado"] or "(sin estado)", [0, 0, 0, set()])
        e[0] += 1
        e[1] += bool(r["correo"])
        e[2] += bool(r["telefono"])
        e[3].add(normaliza(r["municipio"]))
    with open(resumen, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["estado", "registros", "con_correo", "con_telefono", "municipios"])
        for estado, (n, c, t, m) in sorted(por_estado.items()):
            w.writerow([estado, n, c, t, len(m)])
    print(f"  resumen -> {resumen}")


if __name__ == "__main__":
    main()
