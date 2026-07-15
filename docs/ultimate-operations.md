# Football Picks Platform - Guia operativa ultimate

## Objetivo

La plataforma es prepartido. La web debe leer datos desde PostgreSQL, no desde el frontend directamente contra proveedores externos.

## Checklist antes de publicar picks

1. Abrir `Salud del modelo` y comprobar que no haya alertas criticas.
2. Revisar `Administracion > Alertas operativas`.
3. Sincronizar la fecha objetivo si hay datos antiguos.
4. Ejecutar enriquecimiento de fecha para cuotas, estadisticas, formas y mercados.
5. Generar predicciones y revisar `Picks para publicar`.
6. Exportar candidatos desde `Predicciones > Exportar para ChatGPT` si se quiere auditoria externa.

## Modos de seguridad

- `conservative`: menos picks, exige mas EV, mas datos y riesgo bajo/medio.
- `normal`: equilibrio entre volumen, calidad y valor.
- `aggressive`: permite mas candidatos y riesgo alto, pensado para investigacion, no para publicar sin revisar.

El modo se cambia desde `Administracion`. Requiere token admin.

## Reglas de publicacion

Un pick solo debe aparecer como publicable si tiene:

- Partido futuro y prepartido.
- Cuota real verificada, mapeada y reciente.
- Mercado, periodo, seleccion y linea coherentes.
- EV positivo por encima del umbral del modo activo.
- Probabilidad minima.
- Calidad de datos suficiente.
- Riesgo permitido.

Si una regla falla, la tabla muestra `Reglas` y `Motivo`.

## Alertas operativas

`/api/system-alerts` resume problemas accionables:

- Credenciales ausentes.
- Sincronizacion antigua o ausente.
- Errores recientes de proveedor.
- Partidos futuros sin cuotas.
- Partidos futuros sin datos prepartido.

## Datos y proveedores

Las claves se configuran siempre como variables de entorno:

- `API_FOOTBALL_KEY`
- `RAPIDAPI_KEY`

No se deben hardcodear claves en el codigo ni en documentacion.

## Verificacion tecnica

Antes de desplegar:

```bash
python -m pytest backend/tests
python -m compileall backend/app
pnpm --dir frontend run build
```

Despues de desplegar:

```bash
curl https://<railway-url>/api/health
curl https://<railway-url>/api/readiness
curl https://<railway-url>/api/system-alerts
```

## Limitaciones conocidas

Sin historicos suficientes, el rendimiento del modelo debe considerarse preliminar. La plataforma puede estar operativa aunque la calibracion estadistica por mercado requiera mas muestra.
