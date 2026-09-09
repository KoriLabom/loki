---
name: auditar-privacidad
description: Corre la auditoría de privacidad del diff contra origin/main y explica los hallazgos. Usar antes de cualquier merge o push a la rama pública de Loki, o cuando el usuario pida auditar o revisar privacidad antes de publicar.
metadata:
  author: loki
  version: "1.0"
---

Este repo es público. Antes de mergear o pushear a la rama pública, corré
la auditoría:

```
python scripts/auditar_privacidad.py
```

Sin argumentos compara la rama actual contra `origin/main`. Si el diff
que vas a publicar es otro (por ejemplo el de una rama distinta a la
actual, o solo lo agregado al stage), pasá el rango correspondiente,
por ejemplo `python scripts/auditar_privacidad.py --cached` para lo que
está en stage.

## Qué hacer con el resultado

- **Código de salida 0**: no se encontró nada. Podés seguir con el
  merge o el push.
- **Código de salida distinto de cero**: el script imprimió, por cada
  hallazgo, el archivo y la línea, y uno de estos tipos:
  - `ruta_windows` / `ruta_macos`: una ruta con nombre de usuario de la
    máquina de desarrollo.
  - `correo`: una dirección de email.
  - `posible_key_o_token`: algo que parece una API key o un token.
  - `termino_privado`: coincide con un término de la lista privada de
    `config.local.yaml` (el script no imprime cuál término ni la línea
    completa, a propósito, para no repetir el dato sensible).

Para cada hallazgo, mostrale al usuario el archivo y la línea, explicá
qué tipo de dato parece ser, y sugerí sacarlo del diff (moverlo a
`config.local.yaml`, `.env`, o a un ejemplo genérico) antes de intentar
publicar de nuevo. No corras el push ni el merge mientras haya
hallazgos sin resolver.

## Hook `pre-push` opcional

Quien quiera que la auditoría corra sola antes de cada `git push`, puede
crear `.git/hooks/pre-push` (no se commitea, es local de cada clon) con:

```bash
#!/bin/sh
python scripts/auditar_privacidad.py || exit 1
```

Y darle permiso de ejecución (`chmod +x .git/hooks/pre-push` en
Git Bash). Es opcional porque `.git/hooks/` no es parte del repo: cada
persona que clona Loki decide si lo instala.
