# Roche régionale par pixel : essai mis de côté

**Statut :** travail en cours mis de côté le 2026-10-24, sans doc, sans banc de qualité. Tag `piste/roche-regionale`, commit `50b37a5`, sur `8b4e9b9`. Il précède « une seule roche », `jalon/16-une-roche`, et n'a pas été repris.

**Pourquoi ce fichier :** ses mesures n'existaient que dans le message du commit ; elles sont reprises ici.

## Ce qu'il faisait

- **La géologie par pixel :** un bruit de province de 3 000 à 200 km, plus des unités de 40 km à 500 m, `ROCK_UNITS` = 0,5. Le pixel prend la couleur moyenne de sa géologie, sur trois lectures.
- **Une croûte de roche mouillée,** `ROCK_CRUST`, et la forêt tenue sur les pentes, `VEGETATION_HOLD`.
- **Des teintes de strates plus douces :** `STRATA_TINT` = 0,5 ; les badlands à `STRATA_FORMATION_CONTRAST`.
- **Une vue de l'albédo,** `ALBEDO_VIEW`, et `BANC_MATERIAU=albedo` dans `tools/banc_descente.py`, pour suivre la couleur en descente.

## Ce qu'il mesurait

- **Albédo en descente,** de 800 à 25 km, à 14,85° N 123,2° E : le bleu perdait 20 % avant, il gagne 4 %.
- **Contraste vu d'orbite d'une terre aride et rocheuse,** CIELAB sur 15 à 60 km : Blue Marble 2,85 ; avant 0,98, délavé ; la géologie par pixel seule 6,48 ; l'essai 3,59.
- **Les groupes de la palette :** écarts ΔE de 15 à 19 ramenés à 7 à 10.
- **Non mesurés :** `ROCK_CRUST` et `VEGETATION_HOLD`, de simples estimations.

## Ce qu'il en reste

- **Rien dans `main` :** la roche est une seule photo depuis le 2026-10-24, ses strates en couleur (`../spec-roche-organique.md`).
