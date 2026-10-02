# Directorio nacional de cultura municipal (México)

Script para armar una base de datos con **institución, titular, teléfono y correo**
de las áreas municipales de cultura de los 2,400+ municipios del país, a partir de
datos públicos.

## Ejecutar

```bash
python3 extraer_contactos.py --solo-con-contacto            # rápido: CSV nacional del SIC
python3 extraer_contactos.py --solo-con-contacto --fichas   # además saca el nombre del titular de cada ficha (lento)
```

Genera `directorio_cultura_municipal.csv` (se abre en Excel), `resumen_por_estado.csv`
y guarda los CSV originales en `crudos_sic/`.

## Fuentes

| Fuente | Qué trae | URL |
|---|---|---|
| SIC – Instituciones culturales municipales | Institutos/direcciones municipales de cultura: teléfono, correo, web, domicilio | `https://sic.cultura.gob.mx/opendata/d/0_institucion_cultural_mun_directorio.csv` (0 = nacional, 1–32 = por estado) |
| SIC – Centros culturales | Casas de cultura (la mayoría municipales) | `https://sic.cultura.gob.mx/opendata/d/0_centro_cultural_directorio.csv` |
| SIC – Festivales | Festivales y ferias culturales con su contacto | `https://sic.cultura.gob.mx/opendata/d/0_festival_directorio.csv` |
| Plataforma Nacional de Transparencia, art. 70 fracc. VII (Directorio) | Nombre, cargo, teléfono y correo oficial de **todo** servidor público municipal (incluye directores de Cultura, Turismo y Eventos) | https://www.plataformadetransparencia.org.mx |
| SNIM / INAFED | Presidentes municipales y teléfonos del ayuntamiento | https://www.snim.rami.gob.mx |
| Directorios de secretarías estatales de cultura | Enlaces municipales de cultura por estado | p. ej. https://www.cultura.gob.mx/estados_nueva_2019/directorio/ |

## Notas

- Quien contrata artistas para ferias suele ser la **Dirección/Instituto Municipal de
  Cultura**, la **Dirección de Turismo** o un **Patronato de la Feria**. El SIC cubre cultura;
  para Turismo y patronatos, la fuente más completa es el Directorio (fracción VII) de cada
  ayuntamiento en la Plataforma Nacional de Transparencia.
- Los titulares cambian con cada administración municipal (cada 3 años). Revisa la
  columna `ultima_actualizacion` y confirma antes de usar el contacto.
- Son datos de contacto institucional de servidores públicos. Úsalos para fines
  profesionales e incluye en tus correos una forma de darse de baja.
