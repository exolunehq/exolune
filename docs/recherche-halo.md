# Recherche : le halo optique autour du soleil et de la neige

Statut : recherche et première mise en œuvre, le 2026-10-24, piste `piste/halo-optique`. Item 3.11 de `recherche-profondeur-atmospherique.md`. Sources en fin de fichier.

**Dans le jeu, le halo est coupé par défaut.** `MYPLANETENGINE_GLARE` l'active, au lancement direct de l'exe : `tools/lance.ps1` efface les variables (`lancement.md`). Depuis le 2026-10-30, il ne dépend plus des nuages.

## 1. Conclusion

**Un seul halo, linéaire, qui conserve l'énergie, sur l'image avant la courbe de tons.**
- **La loi :** loin d'un point lumineux, le halo décroît comme s E / θ². C'est le halo lointain de l'œil, loi de Stiles-Holladay et terme dominant de l'équation CIE (Vos 2003). C'est aussi celui de la diffusion des surfaces optiques polies.
- **Un seul réglage :** la diffusion s = θ² L / E, en degrés carrés par stéradian, `GLARE_STRAYLIGHT`.
- **Une pyramide suffit :** des demi-images du pixel à l'écran, sommées à poids égaux, décroissent exactement en 1/θ². Chaque octave d'angle porte la même part de lumière, quelle que soit la résolution.
- **La lumière est déplacée, jamais ajoutée :** l'image garde 1 − W de sa lumière, la pyramide répartit W. Pas de seuil, pas de lumière créée.

**Le réglage : un objectif récent, s = 0,3.**
- **Mesuré :** 0,13 à 0,19 % de voile en ISO 18844 pour des objectifs actuels (Koren 2018), soit s ≈ 0,2 à 0,3.
- **Plus fort ailleurs :** les appareils mesurés par McCann et Rizzi, 1 à 8 %, donnent s ≈ 1,4 à 11 ; un œil jeune, s ≈ 10.
- **Pas l'œil :** le halo est linéaire. Devant l'écran, l'œil du spectateur ajoute déjà le sien à tout ce que l'écran montre. L'ajouter dans l'image le compterait deux fois.
- **Essayé à s = 1,7,** un voile de 1 % : le soleil haut devient une boule presque blanche de 4,3° de diamètre, contre 1,9° à s = 0,3. Juste pour un appareil ordinaire, pas discret.

**La neige n'a pas de halo visible, et c'est juste.**
- Une neige au soleil renvoie environ 0,7 fois la luminance d'un blanc parfait.
- À s = 0,3, son voile sur ce qui l'entoure reste sous un niveau de la sortie 8 bits : mesuré, conforme à la loi.
- Le halo des neiges sur les photos vient de la surexposition, ou d'objectifs de plusieurs pour cent de voile.

**Mesuré, section 5 :**
- autour du soleil vu de l'espace, le halo suit la loi à 0,91 à 1,06 près, de 2° à 20° ;
- soleil haut : +33 % de luminance à 2,4°, +9 % à 5°, +3 % à 10° ;
- tremblement inchangé ; pompage du soleil d'un pixel à l'autre, 0,4 % ;
- coût, 0,17 ms en 1280 × 720 sur RTX 4070 Ti.

## 2. Ce que disent les sources

### 2.1 Le halo de l'œil

**Spencer, Shirley, Zimmerman et Greenberg 1995.**
- La diffusion dans la cornée, le cristallin et la rétine étale la lumière d'un point : voile, halo lenticulaire, couronne ciliaire.
- Leur fonction d'étalement somme un cœur gaussien et des termes en 1/θ³ et 1/θ², pondérés selon l'adaptation.
- **Leur raison :** un écran ne peut produire la luminance qui éblouit. On ajoute donc à l'image le halo que l'œil aurait eu.
- Le site de Cornell était injoignable : leurs constantes ne sont pas recopiées ici.

**L'équation CIE de l'éblouissement d'incapacité (Vos 2003, CIE 146:2002).**
- Ψ(θ) = L/E = 10/θ³ + (5/θ² + 0,1 p/θ)(1 + (A/62,5)⁴) + 0,0025 p, en sr⁻¹, θ en degrés, valable de 0,1° à 100°.
- A est l'âge ; p la pigmentation, 0 pour des yeux sombres, 0,5 bruns, 1 bleus ou verts.
- Pour un œil de 25 ans : 27 % de la lumière diffusée au-delà de 0,1°, 8 % au-delà de 1°.
- Au-delà de 2°, le terme en 1/θ² domine : c'est la loi de Stiles-Holladay, 10/θ².
- Van den Berg en tire le paramètre de diffusion, s = θ² Ψ : log s ≈ 1 pour un œil jeune.

### 2.2 Le halo des objectifs

- **ISO 9358 :** l'indice de voile est la lumière reçue au centre d'une tache noire, dans un champ uniformément clair.
- **McCann et Rizzi :** 1 à 8 % du maximum pour les appareils mesurés ; dans le pire cas, le voile limite l'image à environ 25:1.
- **Koren 2018, ISO 18844 :** 0,187 % pour un Canon 90 mm sur Sony A7R II à f/5,6 ; 0,130 % pour un zoom Canon 75-300.
- **Les classes de 1984 pour le 35 mm :** très bon sous 1,5 %, médiocre au-delà de 3 %.
- **La diffusion des surfaces polies** décroît en puissance de l'angle, voisine de 1/θ² : la même loi que l'œil.

**De l'indice à s.** Sous la loi s/θ², une tache de rayon θ1 dans un champ de rayon θ2 reçoit 2π (π/180)² s ln(θ2/θ1), soit 0,0019 s ln(θ2/θ1).
- ISO 9358, tache de 1° dans un champ de 30° : 0,0065 s. Un voile de 1 % donne s ≈ 1,5.
- ISO 18844 au 90 mm, cavité de 0,25° dans un champ de 7° : 0,0064 s. 0,19 % donne s ≈ 0,3.
- **C'est une estimation :** ces sources ne donnent pas la géométrie exacte des mires.

### 2.3 Les techniques temps réel

**Jimenez 2014, Call of Duty: Advanced Warfare.**
- Une pyramide : descente par 13 échantillons, cinq boîtes 2 × 2 qui se chevauchent ; remontée par une tente 3 × 3.
- Sans seuil : le flou se mêle à l'image pour une petite part, l'énergie se conserve.
- Une moyenne de Karis au premier niveau, contre les lucioles. **Écartée ici :** elle éteindrait le soleil.

**Bjørge 2015, le filtre double de Kawase.** La même pyramide, à 5 et 8 échantillons : moins chère, moins ronde.

**Unreal, le halo par convolution.**
- Une FFT de l'image par une image de noyau, qui conserve l'énergie.
- Réservée aux cinématiques et aux machines haut de gamme, pour son coût.
- Utile pour un noyau non radial : étoiles de diffraction, halo lenticulaire. Pas notre besoin.

**Pourquoi la pyramide suffit.**
- Une somme de flous de largeurs doublées, à poids égaux, décroît exactement en 1/r² entre le premier et le dernier niveau.
- La loi est sans échelle : le poids d'un niveau ne dépend ni de la résolution, ni du champ de vision.
- Simulée hors ligne, elle suit la loi à 5 % près de 4 à 128 pixels. Entre axes et diagonales, l'écart reste sous 4 %, 11 % au pire.

### 2.4 Conserver l'énergie, avant la courbe

- **Le halo est un étalement :** la lumière totale de l'image ne change pas.
- **Sur l'image linéaire, avant la courbe :** le soleil, 45 750 fois un blanc au soleil, garde toute son énergie, que la courbe aurait écrasée.
- **Pas de seuil :** un seuil fait apparaître le halo par paliers, et scintiller les surfaces qui le franchissent.

## 3. Combien de halo, et comment le mesurer

**Les ordres de grandeur,** soleil à 40° de hauteur, en fraction d'un blanc au soleil :

| Angle au soleil | Objectif récent, s = 0,3 | Appareil ordinaire, s = 1,5 | Œil jeune, CIE | Notre ciel sans halo |
|---|---|---|---|---|
| 1° | 0,71 | 3,5 | 36 | 0,30 |
| 2° | 0,18 | 0,88 | 6,0 | 0,30 |
| 5° | 0,028 | 0,14 | 0,70 | 0,28 |
| 10° | 0,007 | 0,035 | 0,16 | 0,25 |
| 20° | 0,002 | 0,009 | 0,04 | 0,20 |

**Mesurer contre des photos.**
- **Où lire :** le profil radial de luminance autour du soleil, en lumière linéaire, à pente fixe en échelle log-log.
- **Une photo mêle deux choses :** l'auréole de l'air, diffusion vers l'avant des aérosols, et le halo de l'objectif. Les séparer demande une photo RAW et l'auréole mesurée au photomètre solaire, comme ceux d'AERONET.
- **La mesure propre :** le soleil devant le noir de l'espace. Sans air, l'image est le halo seul : c'est le cas 1 de `tools/banc_halo.py`.
- **Autour de la neige :** le voile ajouté à côté du champ de neige, selon la distance à son bord, comparé à la loi convoluée avec l'image sans halo.

**Notre auréole est plus faible que celle des photos.**
- La phase de Cornette-Shanks à g = 0,7 n'a pas le pic avant étroit des vrais aérosols.
- Notre ciel reste à 0,30 de 1° à 2° du soleil ; un vrai ciel y est bien plus clair.
- **Ce n'est pas au halo de le compenser :** c'est la phase des aérosols, côté atmosphère.

## 4. Ce qui est fait

- **`GlareDown.hlsl`, `GlareUp.hlsl` :** la pyramide, 9 niveaux en 1280 × 720, du demi-écran à 2 × 1 pixels. Descente par les 13 échantillons de Jimenez, remontée par la tente 3 × 3, à poids égaux.
- **`PlanetSettings.hlsli` :** `GLARE_STRAYLIGHT` = 0,3, le seul réglage. Le poids de chaque niveau s'en déduit, 2π ln 2 (π/180)² s.
- **`Glare.cpp` :** `Glare::Initialize` et `Glare::Draw`, entre l'atmosphère et le lissage temporel, avec leurs propres tas de descripteurs. `MYPLANETENGINE_GLARE` l'active ; sans elle, ni ses images ni sa passe.
- **`ToneMap.hlsl` inchangé :** le halo est fondu dans l'image composite, alpha gardé. Le lissage temporel le lisse comme le reste.
- **Le disque du soleil montre la part du pixel qu'il couvre** (`principes.md`) : une ligne de la composition, aujourd'hui `CloudComposite` dans `Clouds.hlsli`. À bord franc, son énergie variait de −10 à +5 % d'une position à l'autre : le halo aurait pulsé.

## 5. Mesures

**Le profil autour du soleil, vu de 2 000 km,** `tools/banc_halo.py`, en fraction d'un blanc au soleil :

| Anneau | 2,4° | 3,5° | 4,9° | 6,9° | 9,8° | 13,9° | 19,6° | 27,7° |
|---|---|---|---|---|---|---|---|---|
| Mesuré | 0,144 | 0,078 | 0,036 | 0,019 | 0,0091 | 0,0052 | 0,0024 | 0,0015 |
| Loi, s = 0,3 | 0,157 | 0,079 | 0,039 | 0,020 | 0,0098 | 0,0049 | 0,0025 | 0,0012 |
| Rapport | 0,92 | 1,00 | 0,91 | 0,99 | 0,93 | 1,06 | 0,99 | 1,24 |
| Œil jeune, CIE | 4,9 | 2,1 | 0,98 | 0,46 | 0,22 | 0,11 | 0,058 | 0,032 |

- **Au bord de l'écran, +24 % :** les derniers niveaux gardent sur l'écran la lumière qui irait au-delà.
- **Même rapport à s = 1,7 :** 0,92 à 1,04 de 2,4° à 20°. La pyramide suit la loi quelle que soit sa force.

**Le soleil dans l'air,** gain de luminance sur l'image sans halo :
- **soleil à 36° sur les montagnes :** +33 % à 2,4°, +18 % à 3,5°, +9 % à 5°, +3 % à 10°, +1,7 % à 14° ;
- **soleil bas, 5° :** halo faible, l'air n'en laisse passer qu'une petite part ; l'auréole de l'air domine.

**La neige, soleil dans le dos :** le voile ajouté à côté du champ de neige vaut 0,0005 à 0,0007 d'un blanc, de 2° à 28° de son bord ; la loi prédit 0,0005 à 0,0007. Écart net à l'image sans halo : sous un niveau de la sortie 8 bits.

**Le tremblement,** `tools/banc_tremblement.py`, avec puis sans halo, lissage avec et sans :
- montagnes au soleil : 0,05 et 0,39, contre 0,05 et 0,40 ;
- désert au soleil bas : 0,00 et 0,01, inchangé ;
- neige : 0,08 et 0,45, contre 0,08 et 0,46.

**Le pompage :** le soleil déplacé par huitièmes de pixel, le halo de 3° à 10° varie de 0,4 % au plus. À bord franc, le disque aurait varié de −10 à +5 %.

**Le coût :** 0,17 ms en 1280 × 720 sur RTX 4070 Ti, médiane de six mesures, vue d'orbite.

## 6. Points ouverts

- **Le soleil hors de l'écran ne donne aucun halo.** Le halo apparaît d'un coup quand son disque entre. Remède possible : le halo du soleil calculé à part, par sa direction.
- **L'éblouissement de l'œil,** s ≈ 10, pour la seule lumière que l'écran ne peut montrer : à décider avec la nouvelle exposition et la nouvelle courbe.
- **Les paliers de la sortie 8 bits** se voient dans le dégradé du halo sur le noir de l'espace. Un tramage d'un demi-niveau à la sortie, dans `ToneMap.hlsl`, les effacerait.
- **Le coût :** des niveaux en flottants 16 bits diviseraient la bande passante par deux. Le soleil, 45 750, frôle leur limite de 65 504 : à éviter tant qu'aucune marge n'est sûre.
- **L'auréole de l'air** de 1° à 3° du soleil, plus faible que sur les photos : la phase des aérosols, côté atmosphère.

## 7. Sources

**Œil**
- Spencer, Shirley, Zimmerman et Greenberg 1995, *Physically-Based Glare Effects for Digital Images*, SIGGRAPH 95 : [article](https://w1.graphics.cornell.edu/pubs/1995/SSZG95.pdf).
- Vos 2003, *On the cause of disability glare and its dependence on glare angle, age and ocular pigmentation*, Clinical and Experimental Optometry 86(6), 363-370 ; CIE 146:2002, *CIE equations for disability glare*.
- L'équation générale, recopiée et discutée par Bará et Bao-Varela 2023, *Skyglow inside your eyes* : [article](https://arxiv.org/abs/2212.09103).
- Van den Berg, Franssen, Kruijt et Coppens 2013, *History of ocular straylight measurement: A review*, Z. Med. Phys. 23, 6-20 : [doi](https://doi.org/10.1016/j.zemedi.2012.10.009).

**Objectifs**
- ISO 9358:1994, indice de voile et fonction d'étalement : [ISO](https://www.iso.org/standard/17042.html).
- McCann et Rizzi, voile des appareils et limites des images HDR, ECVP 2006, JSID 2007 et 2009 : [archives de Milan](https://air.unimi.it/handle/2434/192417).
- Koren 2018, mesures ISO 18844 et dynamique des appareils, Electronic Imaging : [article](https://www.imatest.com/wp-content/uploads/2018/01/EI2018_Norman_Koren_final_paper.pdf).
- Classes du voile des objectifs 35 mm, SPIE 467, 1984 : [résumé](https://proceedings.spiedigitallibrary.org/conference-proceedings-of-spie/467/0000/Simplified-Method-For-Measuring-And-Assessing-The-Veiling-Glare-Of/10.1117/12.941584.full).
- Talvala, Adams, Horowitz et Levoy 2007, *Veiling Glare in High Dynamic Range Imaging* : [projet](https://graphics.stanford.edu/papers/glare_removal/).

**Temps réel**
- Jimenez 2014, *Next Generation Post Processing in Call of Duty: Advanced Warfare*, SIGGRAPH : [diapositives](https://www.iryoku.com/next-generation-post-processing-in-call-of-duty-advanced-warfare/).
- Bjørge 2015, *Bandwidth-Efficient Rendering*, cours SIGGRAPH 2015 *Moving Mobile Graphics*.
- Unreal Engine, le halo standard et par convolution : [documentation](https://dev.epicgames.com/documentation/en-us/unreal-engine/bloom-in-unreal-engine).
