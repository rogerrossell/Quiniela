# Quiniela

Tauler en català amb previsió de resultats, seguiment d'encerts i programació de les actualitzacions.

## Web

- `site/dist/index.html`: previsió i seguiment.
- `site/dist/programacio.html`: dates en què cal tenir el Mac disponible.
- `outputs/programacio.json`: calendari verificat i estats d'execució.
- `outputs/seguiment.json`: previsions congelades, resultats i revisions.

Les pàgines són estàtiques. Es poden obrir localment o servir des de `site/dist`. No consulten marcadors en directe ni executen tasques programades. L'automatització de Codex és una configuració externa que necessita el Mac disponible amb l'app oberta.

## Regenerar

Amb Python 3.9 o posterior:

```sh
python3 work/build_dashboard.py
```

No requereix llibreries externes. El sistema ha de disposar de les dades de fusos horaris per a `Europe/Madrid`.

El generador crea les dues pàgines a `site/dist` i còpies a `outputs`. Les dates de previsió es calculen dos dies naturals abans del primer partit i les revisions un dia després de l'últim, a les 10:00. La pàgina recomana preparar el Mac a les 09:50 i mantenir-lo disponible fins a la finalització. Les jornades ajornades s'han de reprogramar a la font de dades.

## Model experimental

`outputs/model_quiniela_v1.py` calcula probabilitats 1/X/2 amb Poisson, gols i seu, i ajustos heurístics. Exemple:

```sh
python3 outputs/model_quiniela_v1.py outputs/dades_j7.json
```

Sense validació històrica, xG ni garantia d'encert. La jornada 7 conté cinc prediccions prèvies al partit; els altres cinc partits queden exclosos de l'avaluació. No s'han de modificar les prediccions publicades després de conèixer el resultat.

Les mètriques consideren només partits amb previsió i resultat final verificat. Cal preservar la data de tall, les fonts i la versió del model. Cap compra d'apostes s'executa des d'aquest projecte.

Aquest repositori no inclou credencials, identificadors de xats, configuració privada d'automatitzacions ni dades personals.

## Quatre apostes per jornada

El generador calcula les quatre columnes 1/X/2 diferents amb major probabilitat conjunta, amb probabilitats sense arrodonir i assumint independència entre partits. L’objectiu és encertar tots els signes (14 en un cupó complet), no qualsevol premi ni rendibilitat. El Ple al 15 fa servir la categoria de gols més probable i es mostra separat del percentatge de 14 encerts.

Sense cupó oficial verificat, es mostren només combinacions parcials. Per activar el cupó complet, la jornada ha d’incloure `official_coupon`: `verified_at`, `source`, `deadline`, `match_indices` (14 índexs diferents, base zero, de `matches` en ordre oficial) i `pleno15` amb `home`, `away`, `kickoff` i `probabilities` (les 16 categories `0-0` a `M-M`, on M és 3+ gols). Tots els partits han de tenir previsió anterior a l’inici i al tancament. Cal verificar aquests camps amb SELAE; mai inventar partits ni probabilitats absents.

`work/coupons.py` s’executa en regenerar el tauler. La revisió de resultats no altera les columnes. Comprovació del càlcul: `python3 work/test_coupons.py`.
