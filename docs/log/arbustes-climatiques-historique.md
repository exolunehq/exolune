# Historique des arbustes climatiques

**2026-10-27 : première collection, non retenue.**
- Douze formes générées avec les mêmes familles, en faisant surtout varier les paramètres de port et de densité.
- Les planches CPU montrent des silhouettes encore trop apparentées en vase et un pied trop nu.
- Le gris-vert des formes arides ne suffit pas à différencier leur architecture.
- Cette première piste reste dans `assets/foliage/climate_shrubs/`, sans être le défaut du candidat.

**2026-10-27 : seconde collection.**
- Boréal : touffe basse irrégulière ; désert : fourches latérales ; steppe : touffe de sol et quelques tiges dressées.
- Montagne : rameaux presque horizontaux ; tempéré : trois centres feuillus ; tropical : tiges séparées et grandes feuilles alternes courbées.
- Deux orientations et une planche à l'allométrie moteur sont examinées avant les bakes finaux.
- La couleur, les normales et le masque du bois sont extraits explicitement de la tuile source 0 ; les feuilles utilisent la tuile 1.
- Les douze architectures réutilisent les photographies de feuilles du Searsia Lucida sous CC0 ; elles ne décrivent pas douze espèces réelles distinctes.

**La sélection :**
- Une première somme de poids avec un plancher tempéré de 0,08 laisse trop de familles non adaptées dans les climats francs.
- Elle est remplacée avant les comparatifs par une partition hiérarchique continue, sans plancher forcé.
- Les six cas climatiques extrêmes sont contrôlés sur CPU ; les poids restent positifs et de somme 1.

**Le protocole GPU :**
- Les familles partagent les six régions existantes de 192 Mio ; les comptes précèdent le calcul des sous-plages, puis leur remplissage.
- Le préfixe ne doit pas seulement devenir `StartInstanceLocation` : `SV_InstanceID` commence à zéro selon la [spécification Direct3D, §8.18](https://microsoft.github.io/DirectX-Specs/d3d/archive/D3D11_3_FunctionalSpec.htm#Instancing).
- Les commandes indirectes portent donc aussi l'adresse du SRV racine ajustée à la sous-plage.
- La compilation isolée réussit ; le nouveau pipeline sans catalogue retrouve les totaux de population de la référence sur les quatorze premières vues, sans dépassement.

**État courant :** `../arbustes-climatiques.md`.

**Les comparatifs moteur :**
- Quatorze vues avec et sans catalogue, sur le même exécutable : graines et positions identiques après tri, mêmes totaux par espèce, aucun dépassement.
- Quatre voisins complètent les cadrages où il n'y avait que trois ou cinq arbustes.
- Familles observées : désert et steppe secs, tempéré humide et tropical francs ; mélanges boréal/montagne et montagne/tempéré près des limites.
- Une première série de temps signale un coût élevé ; les appels sont regroupés par représentation et les commandes vides sont ignorées via le compteur indirect GPU.
- Les quatorze BMP restent identiques à l'octet près après cette réorganisation ; deux à treize commandes sont actives selon la vue sur vingt-huit possibles.
- Le coût mémoire des représentations augmente de 466 967 464 octets ; les six files restent à 192 Mio.

**Le banc de qualité :**
- Les vingt-quatre sites terminent sans blocage GPU, mais le critère strict échoue face au candidat précédent sur deux p95 : gap sable/50 m +10,15 %, gap sol/12 m +20,83 %.
- Les trois écarts précédents ne sont pas effacés ; cinq seuils dépassent l'avant de la passe de bouquets. Les métriques restent inchangées.
- Le canonique condensé à trente sites donne quatorze dépassements ; il ne représente pas les mêmes lieux que ces vingt-quatre sites.
- Le catalogue reste un candidat de jugement, sans être déclaré validé par le banc.

**Les temps, limites d'interprétation :**
- La première série sans readback donne 39,39 ms de dessin médian pour V2 ; une répétition du même binaire donne 7,61 ms. La charge de la machine varie donc fortement.
- L'optimisation produit des images identiques ; ses médianes sont de 4,81 puis 4,48 ms sur les mêmes six lieux, mais le facteur brut ne peut pas lui être attribué seul.
- Sur le même binaire optimisé, les médianes par lieu ancien/V2 sont proches, avec quelques hausses : boréal 4,14/4,76 ms ; désert 0,75/0,60 ; maquis 3,10/3,07 ; montagne 3,67/3,51 ; lisière 6,98/7,44 ; tropical 8,97/9,08.
- Aucun gain global de FPS n'est établi. Les fichiers `synthese_perf_finale.json` et `optimisation_perf.json` gardent les séquences et le contexte.

**Le vol de jugement, jusqu'au 2026-10-30 :**
- `tools/lance_planet_foliage.ps1` choisit le catalogue V2 et `x64/FoliageShrubs/MyPlanetEngine.exe`.
- `-Assets assets/foliage/volume_look_normals` retrouve l'arbuste unique précédent ; l'exécutable récent sait lire les deux jeux de données.
- Retirés le 2026-10-30 avec les modes du feuillage : le catalogue est requis, et sans lui le moteur ne dessine aucune plante. Tag `jalon/24-vegetation-detaillee-main`.
