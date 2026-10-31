# Historique de la mer

## Premier noyau remplacé sur la piste FFT

## 8. Fait : la mer animée, piste `piste/mer-animee` (2026-10-25)

**En bref :** le vent, le reflet du soleil et du ciel, les moutons et les vagues animées dans les pixels, tout dans `Sea.hlsli`. La pente a toujours la variance de Cox et Munk : montrée par les vagues ou perdue dans la rugosité du reflet. Le reflet et les moutons gardent leur moyenne de l'orbite au ras de l'eau.

**Ce qui est fait :**
- **Le vent, `SeaWind` :** la circulation par latitude de la section 2, le temps de 3 000 à 300 km, 3 m/s par axe, les rafales et nappes calmes de 100 à 5 km, un facteur e^X de ±30 %. La houle, la couche 4, n'est pas faite ; la mer est levée partout, sans fetch.
- **Le reflet, `ReflectOnWater` :** Cox-Munk anisotrope autour de la pente montrée, Fresnel de l'eau au pied de la facette (0,0204), masquage de Smith ; le ciel marché depuis l'eau par `IntegrateScattering`, 6 pas, au Fresnel moyen de Bruneton. Une seule fonction pour la mer et, à la fusion, le sable mouillé.
- **Les vagues :** 168 ondes, 14 octaves de 512 m à 6 cm, 12 directions chacune, une par secteur. Pierson-Moskowitz : la même pente par octave, le pic à 0,83 U². Étalement cos⁴ de la demi-différence au vent ; dispersion en eau profonde, capillarité comprise.
  - **Chaque onde montre sa moyenne sur le pixel,** un sinus cardinal par côté, et s'efface de 8 à 2 pixels par longueur d'onde. Ses crêtes, courtes, perdent leur phase en deux longueurs d'onde ; le pixel les moyenne aussi le long d'elles.
  - **Ce qu'elles ne montrent pas élargit le reflet :** variance perdue = Cox-Munk moins variance montrée, axe par axe.
  - **Une somme d'ondes au pixel, pas une FFT :** ni ressource ni passe nouvelle, un filtrage exact onde par onde, le vent du pixel sur chaque amplitude. Ses limites : un motif plus pauvre qu'une FFT de près, et le coût.
- **Leur plan :** tangent à la caméra, porté sans tourner quand elle vole ; son origine garde le chemin parcouru, en double. Les phases sont calculées sur le CPU, `D3DApp::UpdateWaves`. Un saut de la caméra repart d'une origine tirée du lieu.
- **Le temps :** l'horloge en vol, 1/60 s par image en capture et aux bancs ; `MYPLANETENGINE_TIME="début [vitesse]"`.
- **Les moutons :** la part de Monahan, sa moyenne sur les rafales que le pixel ne montre pas.
  - **De près,** là où les vagues d'une demi-longueur de pic se groupent : le carré de leur enveloppe au-delà d'un seuil. L'écume naît sur la crête, la suit, puis s'efface sur un cinquième de période, en dentelle.
  - **Le seuil garde la moyenne de Monahan :** e^-u pour l'enveloppe d'une somme gaussienne. Au-delà de 5,5 %, en tempête, une vieille écume uniforme fait le reste.
  - **L'écume fraîche vaut 0,55, la vieille 0,1 :** 0,22 en moyenne, Koepke.
- **La couleur de l'eau :** un type d'eau par la latitude, plus vert en eau froide et sur les plateaux. Le fond se voit, Maritorena : sable mouillé, atténuation par canal. Sa moyenne est exacte sur les profondeurs du pixel, loi normale tronquée à la côte. Le dégradé sur 3 000 m est retiré.
- **Le lissage temporel :** un pixel de mer qui montre des vagues n'en a plus ; la distance passée à l'atmosphère y est négative. Chaque image y montre déjà la moyenne du pixel.

**Mesures,** RTX 4070 Ti partagée, 1280 × 720 :
- **Le reflet d'orbite contre Cox-Munk,** `tools/banc_mer.py reflet`, à 400 km, soleil à 20° du zénith, pixel par pixel au vent du pixel :

| Vent médian | > 0,5 du max. | 0,2 à 0,5 | 0,05 à 0,2 | 0,01 à 0,05 | Écart moyen |
|---|---|---|---|---|---|
| 2,6 m/s | 0,994 | 0,992 | 0,992 | 0,993 | 1,1 % |
| 6,6 m/s | 0,994 | 0,992 | 0,992 | 0,997 | 1,4 % |
| 13,0 m/s | 0,995 | 0,992 | 0,990 | 1,003 | 1,9 % |
| 14,6 m/s | 0,992 | 0,991 | 0,986 | 1,009 | 2,0 % |
| 20,2 m/s | 0,989 | 0,978 | 0,977 | 1,038 | 3,6 % |

  - Profils dans le plan du soleil : `images/mer-reflet-cox-munk.png`. Les nappes calmes y font les pics, comme sur les images de la NASA.
- **La descente,** `tools/banc_mer.py descente`, de 1 500 km à 10 m, soleil à 20° du zénith, trois sites de 6,7, 10,5 et 26,6 m/s :
  - **le reflet moyen** reste à 2 % de Cox-Munk de 1 500 km à 200 m. Plus bas, la vue de 10 à 80 m ne couvre qu'une part d'un groupe de vagues : sur 16 instants, −8 à +11 % ;
  - **la part de moutons** est celle de Monahan à 1 % près de l'orbite à 3 km. De près : à ±8 % à 10,5 et 26,6 m/s ; 20 % dessous à 6,7 m/s, où le seuil est haut et la bande n'a que quelques ondes. À 10 m, une vue de 12 m voit rarement un mouton.

| Hauteur | Reflet / Cox-Munk, 10,5 m/s | Moutons, vus / Monahan, 10,5 m/s | Moutons, 26,6 m/s |
|---|---|---|---|
| 1 500 km | 0,994 | 4,12 / 4,10 % | 8,08 / 8,04 % |
| 100 km | 0,985 | 13,00 / 12,99 % | 21,75 / 21,73 % |
| 10 km | 0,992 | 1,18 / 1,18 % | 22,59 / 22,51 % |
| 1 km | 0,992 | 1,13 / 1,15 % | 27,69 / 27,66 % |
| 200 m | 0,995 | 1,10 / 1,15 % | 28,43 / 27,89 % |
| 30 m | 0,973 | 1,07 / 1,16 % | 29,53 / 27,69 % |

  Le vent change d'une hauteur à l'autre parce que la vue couvre plus ou moins de rafales ; la comparaison se fait au vent de chaque pixel.
- **Le scintillement,** `tools/banc_tremblement_mer.py`, maillage qui glisse, caméra fixe, écart moyen d'une image à l'autre sur 255 :

| Vue | Sol hors mer, avec / sans lissage | Mer figée | Mer animée, avec / sans lissage | Contraste du détail, avec / sans lissage |
|---|---|---|---|---|
| Côte, 120 m | 0,02 / 0,08, figée comme animée | 0,05 | 0,55 / 0,56 | 8,52 / 8,52 |
| 20 m, mer fraîche | pas de sol | 0,05 | 2,29 / 2,29 | 15,69 / 15,69 |
| 500 m, mer modérée | pas de sol | 0,02 | 0,38 / 0,38 | 9,59 / 9,59 |

  - **Hors de la mer, rien ne change** quand elle bouge. Le banc de tremblement habituel, mer figée, à la côte : 0,01 / 0,04 avant, 0,02 / 0,03 après.
  - **La mer ne tremble pas avec le maillage,** 0,05 : ses vagues sont calculées sur la planète, pas sur les sommets.
  - **Son mouvement n'est plus étalé :** avec le lissage temporel, il gardait 70 % du contraste de ses vagues à 20 m, 10,48 contre 14,70, et 68 % de son mouvement. Sans lissage sur les vagues, les deux cas sont égaux.
- **Le coût,** l'image la plus rapide de chaque capture, quatre captures, contre la base :

| Vue | Base | Mer animée |
|---|---|---|
| 20 m, mer fraîche | 1,20 ms | 3,22 ms |
| 500 m, mer modérée | 0,86 ms | 2,32 ms |
| Côte, 120 m | 2,12 ms | 3,95 ms |
| Orbite, 1 000 km | 0,59 ms | 1,00 ms |
| Montagne, 1,9 km, sans mer | 5,22 ms | 5,58 ms, au bruit près |

  - **D'orbite, +0,4 ms :** l'étape 1 seule, vent, reflet et ciel. **Près de l'eau, +1,5 à 2 ms :** les vagues, plein écran.
  - Le GPU servait à sept autres moteurs en même temps ; la moyenne des images doublait ces écarts. La barre de titre donne maintenant l'image la plus rapide.
- **Le banc de qualité :** la terre est inchangée au pixel près, deux vues comparées ; le rendu de la terre ne passe pas par la mer.

**Fusion avec `plages` (`c87dcd9`),** faite à l'essai et compilée, tag `piste/essai-fusion-mer-plages` :
- **La part de mer :** celle de `plages`, `LandShare` et `ShoreSpread` ; `SeaSurfaceAt` prend leur étalement, `ShoreSpread`, au lieu d'`elevationSpread`, pour le fond vu.
- **`WaterSheen` disparaît :** le sable mouillé appelle `ReflectOnWater`, variance de Beckmann la moitié du carré de sa rugosité, `0,5 (0,04 + slopeSpread²)`.
- **L'albédo de la mer sur 3 000 m disparaît :** `albedo = ground.albedo`, `wet = ground.wet`, et la radiance se partage avec la mer par `sea` à la fin.

**Reste :**
- **Les vagues en géométrie près de la caméra :** déplacement vertical et horizontal des ondes de plus de deux mailles, sur la surface de l'eau seule, à classer dans `geometrie.md`.
- **Le déferlement à la côte :** vagues amorties et réfractées par la profondeur, H > 0,78 d, écume de bord en part du pixel, avec `plages`.
- **Le coût de près, une FFT :** la somme d'ondes coûte 1,5 à 2 ms en plein écran près de l'eau. Trois ou quatre cascades FFT la remplaceraient, la comptabilité des variances inchangée.
- **La houle, le fetch, les lacs** ; la couleur contre Blue Marble ; le type d'eau sans le bruit régional du climat ; les moutons de près à vent faible, 20 % sous Monahan.
