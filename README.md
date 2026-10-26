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

La v0.1 original no tenia validació històrica; ara es compara amb candidats a `outputs/historical_evaluation.json`. Encara sense xG ni garantia d’encert. La jornada 7 conté cinc prediccions prèvies al partit; els altres cinc partits queden exclosos de l'avaluació. No s'han de modificar les prediccions publicades després de conèixer el resultat.

Les mètriques consideren només partits amb previsió i resultat final verificat. Cal preservar la data de tall, les fonts i la versió del model. Cap compra d'apostes s'executa des d'aquest projecte.

Aquest repositori no inclou credencials, identificadors de xats, configuració privada d'automatitzacions ni dades personals.

## Quatre apostes per jornada

El generador calcula les quatre columnes 1/X/2 diferents amb major probabilitat conjunta, amb probabilitats sense arrodonir i assumint independència entre partits. L’objectiu és encertar tots els signes (14 en un cupó complet), no qualsevol premi ni rendibilitat. El Ple al 15 fa servir la categoria de gols més probable i es mostra separat del percentatge de 14 encerts.

Sense cupó oficial verificat, es mostren només combinacions parcials. Per activar el cupó complet, la jornada ha d’incloure `official_coupon`: `verified_at`, `source`, `deadline`, `match_indices` (14 índexs diferents, base zero, de `matches` en ordre oficial) i `pleno15` amb `home`, `away`, `kickoff` i `probabilities` (les 16 categories `0-0` a `M-M`, on M és 3+ gols). Tots els partits han de tenir previsió anterior a l’inici i al tancament. Cal verificar aquests camps amb SELAE; mai inventar partits ni probabilitats absents.

`work/coupons.py` s’executa en regenerar el tauler. La revisió de resultats no altera les columnes. Comprovació del càlcul: `python3 work/test_coupons.py`.


## Avaluació històrica i política des del 26/10/2026

- Fonts: `historical/raw/`, quatre temporades SP1/SP2 de Football-Data.co.uk (font secundària), amb URLs, data de descàrrega i SHA-256 a `historical/manifest.json`.
- 2022/23–2023/24: historial inicial. 2024/25: selecció de paràmetres per competició. 2025/26: prova reservada, sense reselecció.
- Protocol conservador mensual: el dia 1 de cada mes s’usa un tall dos dies abans a les 00:00 Europe/Madrid, excloent tots els partits d’aquella data o posteriors. No s’actualitza dins el mes. No és una reproducció dels cupons oficials.
- `work/historical_evaluation.py`: model v0.1 reproduït, freqüències de lliga, probabilitats iguals, candidat Poisson amb atac/defensa, regularització i pes temporal. La variant DC ajusta rho en un segon pas. La temperatura només s’escull amb validació.
- Les quotes de tancament normalitzades són una referència retrospectiva separada, amb informació posterior al tall; no decideixen paràmetres ni adopció.
- Informe visible: `site/dist/model.html`; prediccions, talls i ajustos reproduïbles: `outputs/historical_predictions_SP*.json`.

Per executar la recerca, calen les dependències de `work/requirements-evaluation.txt`:

```sh
python3 work/historical_evaluation.py
python3 -m unittest discover -s work -p 'test_historical_evaluation.py'
python3 work/build_dashboard.py
```

La web continua regenerant-se amb biblioteca estàndard, sense instal·lar aquestes dependències.

### Regla per a la pròxima previsió

Llegir `outputs/model_policy.json`. Primera: el motor `outputs/model_quiniela_v2.py` està preparat per usar el candidat validat només amb un historial verificat i un snapshot del tall mensual. Segona i Liga F mantenen v0.1; no atribuir a Liga F la validació d’altres competicions. No s’activa cap canvi en partits ja publicats.

1. Recollir i verificar un historial SP1 d’almenys 500 finals dels dos anys anteriors al tall mensual, amb data final real, ordre local/visitant i fonts. No confondre una data inicial d’un ajornat amb la data del resultat final. Equips ascendits sense historial SP1: prior neutral documentat, confiança baixa.
2. Preparar JSON `history.json` amb `sources` i `matches`: cada partit porta `division`, `date` ISO de finalització, `home`, `away`, `gh`, `ga`.
3. Exportar amb `python3 work/export_strength_snapshot.py --history history.json --cutoff <tall-ISO-amb-zona> --output snapshot.json`. Requereix les dependències de recerca i aplica el protocol mensual validat; no usar un ajust setmanal com si tingués aquesta validació.
4. Preparar entrada amb `cutoff`, `strength_snapshot` i `matches`. Cada partit usa els camps v0.1 més `competition_code` (`SP1`, `SP2`, `LIGA_F`). A SP1, cada equip porta `history_key` exacte de l’historial. No fer correspondències aproximades silencioses.
5. Executar `python3 outputs/model_quiniela_v2.py entrada.json`. Només genera per a partits no començats, rebutja talls futurs o snapshots incompatibles, i conserva `reference_v01` per comparar prospectivament sense sumar dues previsions d’un mateix partit.
6. Conservar fonts, snapshot, versió per partit i data real de publicació. Les quatre columnes s’han de generar amb les probabilitats noves sense arrodonir només per a una jornada nova amb cupó oficial verificat. Si falta historial, no afirmar que s’ha usat v0.2: documentar v0.1 o ometre el partit.

Primera, prova reservada: v0.1 191/380 (50,3%), candidat 204/380 (53,7%), Brier 0,603 → 0,582, pèrdua logarítmica 1,010 → 0,981. Els intervals aparellats de blocs de 28 dies afavoreixen el candidat contra v0.1 i freqüències de lliga en totes dues mètriques. Evidència exploratòria d’una temporada; no garanteix millora futura ni premis.

Segona: v0.1 217/462 (47,0%), candidat 212/462 (45,9%); no s’adopta el candidat. La correcció DC i el calibratge per temperatura no s’apliquen a Primera perquè la selecció de validació no els avala.

Les simulacions històriques no entren a la taxa d’encert real. Els resultats i les previsions publicades continuen congelats. Per provar noves variants després d’haver vist 2025/26 cal una nova prova temporal independent; no reoptimitzar contra aquesta mateixa temporada.
