# Recherche : dire la distance par l'atmosphère

Statut : recherche, le 2026-10-24. Aucun code changé, moteur non lancé : tout vient de la lecture du code et des sources, listées en fin de fichier. Étapes 2 à 5 faites le même jour, visibilité de 40 km (`journal-planete.md`, la brume de la couche limite). Le 2026-10-25, la couche suit le sol régional, lu sur la carte de la planète (3.5 ; `journal-planete.md`, la carte de la planète). Le banc de l'étape 1 reste à faire.

**Dans le jeu :** l'air passe par la composition des nuages (`spec-nuages.md`, `CloudAirPiece`), 12 pas vers une surface, 24 vers le ciel. La brume sur le sol régional le long de la vue y est rendue le 2026-10-30, à juger en vol (`tools/tests/2026-10-30-lumiere.txt`) ; jusque-là, son air était celui d'un sol au niveau de la mer. La section 2 décrit l'état d'avant ces travaux.

## 1. Conclusion et ordre de travail

**Notre air est presque parfaitement pur : c'est la cause principale du manque de profondeur.**
- Nos aérosols sont ceux de la démo de Bruneton, repris tels quels par Hillaire et par Unreal : une épaisseur optique de 0,005.
- La moyenne mesurée par satellite est de 0,19 sur les terres et de 0,13 sur les océans.
- La visibilité au sol vaut donc 217 km chez nous. Un beau jour ordinaire en donne 20 à 60.
- À 10 km, une crête garde 84 % de son contraste chez nous, 38 % par temps clair ordinaire. Le second plan ne se détache pas du premier.

**Le « léger flou de distance » cherché est ce voile, pas un flou.**
- L'air retire le même contraste à toutes les échelles. Il n'enlève aucun détail.
- L'œil perd d'abord les détails fins peu contrastés : la douceur du lointain vient seule.
- Une vraie profondeur de champ est fausse à notre champ de vision, et fait lire le paysage comme une maquette.

**L'effet d'altitude vient du même air, sans règle par altitude.**
- Au sol, le voile croît avec la distance : premier plan net, plans successifs de plus en plus pâles et bleus.
- Au-dessus de la couche de brume, il dépend de l'angle de vue et non de la distance : tout est « loin pareil ».
- Il suffit que l'air ait la bonne quantité et la bonne hauteur, et que le calcul le voie à toute altitude.

**L'ordre recommandé : corriger l'existant d'abord.** Les étapes 2 à 5 ne touchent que l'atmosphère existante, pour un coût nul.
1. **Le banc de profondeur :** voile, couleur et contraste selon la distance, sur des photos à profondeur connue et sur nos rendus. Rien ne se règle sans lui.
2. **Des pas qui montrent la moyenne de l'air :** vue d'orbite, le calcul compte aujourd'hui 4,6 fois trop peu de brume. Invisible tant qu'elle est faible ; une brume réaliste muterait en descente. C'est le prérequis.
3. **La visibilité réglée sur les photos :** un seul réglage, la visibilité en km, d'où se déduit la densité des aérosols. Départ vers 40 km. Le plus gros gain.
4. **La couleur et la phase des aérosols :** un voile un peu plus bleu, exposant d'Ångström vers 1,3 ; une asymétrie de 0,8 ramenée vers 0,7.
5. **La couche limite :** une brume à sommet doux vers 1,5 à 2 km, au lieu d'une exponentielle seule. Elle fait la bande de brume vue d'avion.
6. **Les ombres portées du relief, puis les rayons de soleil :** le plus fort indice restant pour séparer les plans. Une spec à part, au coût réel.

**À ne pas faire :** profondeur de champ sur le paysage, filtre de flou selon la distance, miroitement de chaleur.

**Plus tard, avec la météo :** brouillards de vallée, ombres des nuages, exposition réglée sur l'éclairement, voile optique autour du soleil.

## 2. Ce que nous avons

**La perspective aérienne est calculée à chaque pixel, une seule fois** (`AtmospherePass.hlsl`).
- Un rayon va de la caméra au terrain, à la distance que le terrain écrit dans l'alpha de l'image HDR, en flottant 32 bits.
- 12 pas réguliers pour le terrain, 32 pour le ciel. Chaque pas prend la densité de l'air en son milieu.
- Diffusion simple de Rayleigh et de Mie à chaque pas, plus la diffusion multiple de la table de Hillaire.
- Le soleil n'y est masqué que par la Terre : aucune ombre du relief, ni dans l'air ni au sol.

**L'air, dans `PlanetSettings.hlsli`, est celui de la démo de Bruneton 2017 :**

| Composante | Coefficient au niveau de la mer | Hauteur d'échelle | Phase |
|---|---|---|---|
| Rayleigh | 5,8, 13,6 et 33,1 × 10⁻³ km⁻¹ à 680, 550 et 440 nm | 8 km | Rayleigh |
| Mie | diffusion 4,0 × 10⁻³, extinction 4,4 × 10⁻³ km⁻¹, sans couleur | 1,2 km | Cornette-Shanks, g = 0,8 |
| Ozone | absorption seule, en tente de 10 à 40 km | sans objet | sans objet |

- **L'altitude est prise au-dessus de la mer.** Un sol à 4 km ne voit que 3,6 % de la brume du niveau de la mer.
- **Épaisseur optique des aérosols :** 4,44 × 10⁻³ × 1,2 = 0,005. Celle de Rayleigh à 550 nm : 0,11.

**La visibilité au sol, par la loi de Koschmieder :** V = 3,912 / β, avec β l'extinction à 550 nm.
- β = 13,6 × 10⁻³ + 4,4 × 10⁻³ = 18,0 × 10⁻³ km⁻¹, donc **V = 217 km.**
- Rayleigh seul donnerait 289 km : notre air est aux trois quarts moléculaire.
- Le contraste ne baisse de moitié qu'en 38 km.

**Ni brouillard en hauteur, ni couche de brume au sol.** La seule brume est l'exponentielle de Mie. Pas de nuages, pas de brouillard local, pas de volume éclairé.

**L'éclairage du terrain** (`PixelShader.hlsl`) :
- le soleil filtré par l'air au-dessus du point ;
- le ciel d'un sol horizontal, pondéré par l'orientation de la normale et par la cavité des textures ;
- des micro-ombres de cavité.
- **Manquent :** les ombres portées du relief et le ciel caché par les versants des vallées.

**Le passage à l'écran** (`ToneMap.hlsl`) :
- lissage temporel, 10 % d'image nouvelle, reprojection exacte ;
- compression des hautes lumières de Khronos PBR Neutral : identité sous 0,76, puis fondu vers le blanc, désaturation 0,15 ;
- sortie sRGB par le matériel.
- **Pas d'exposition :** une radiance de 1 donne le blanc. Ni exposition automatique, ni halo, ni profondeur de champ, ni étalonnage.

**Un défaut d'échantillonnage, invisible aujourd'hui :**
- Vu d'orbite, le rayon entre dans l'air à 100 km ; ses 12 pas font 8,3 km.
- Le dernier pas lit la brume à 4,2 km d'altitude : 3 % de sa densité au sol. La moyenne vraie sur ce pas est de 14 %.
- La brume y est donc comptée 4,6 fois trop faible ; Rayleigh, 5 % trop faible.
- À 10 km d'altitude, les pas font 0,8 km et l'erreur tombe à 2 %.
- Avec une brume réaliste, elle grossirait d'un facteur 4 en descendant : une mutation, contraire aux principes.

**Ce que montrent les images.** `images/actuel-cote.png` contre l'image cible `images/cible-cote.jpg` :
- chez nous, le ciel reste bleu saturé jusqu'à l'horizon, et la mer bleu sombre jusqu'à la ligne ;
- sur la cible, l'horizon blanchit et la mer pâlit au loin.
- Les bords flous de la cible sont un effet de bascule, à ne pas copier (3.13).

## 3. Les indices, par impact et coût

| # | Indice | Impact | Coût | Chez nous |
|---|---|---|---|---|
| 3.1 | Voile de l'air : contraste et clarté selon la distance | très fort | nul, un réglage | trop faible, V = 217 km |
| 3.2 | Pas d'intégration justes | prérequis | nul | brume sous-comptée vue d'en haut |
| 3.3 | Couleur du voile, désaturation | fort, vient avec 3.1 | nul | aérosols sans couleur |
| 3.4 | Brume plus claire vers le soleil | moyen, fort à contre-jour | nul | g = 0,8, un peu fort |
| 3.5 | Couche limite, hauteur de la brume | fort en altitude, moyen au sol | faible | exponentielle seule |
| 3.6 | Ombres portées, ciel caché des vallées | très fort pour les plans | élevé | absent |
| 3.7 | Rayons de soleil, air à l'ombre | moyen, selon la scène | 1 ms | piste `rayons-soleil`, `recherche-rayons.md` |
| 3.8 | Brouillards de vallée | fort mais selon la météo | moyen à élevé | absent |
| 3.9 | Ombres des nuages | fort | élevé, il faut des nuages | absent |
| 3.10 | Exposition | faible pour la profondeur | faible | fixe |
| 3.11 | Voile optique près du soleil | faible | faible | fait, `recherche-halo.md` |
| 3.12 | Flou atmosphérique | négligeable à notre pixel | sans objet | à ne pas faire |
| 3.13 | Profondeur de champ | contre-productif | sans objet | à ne pas faire |
| 3.14 | Miroitement de chaleur | négligeable | sans objet | à ne pas faire |
| 3.15 | Premier plan : détail, micro-ombres | fort | fait | en place |

### 3.1 Le voile de l'air

**Physique.**
- La lumière de l'objet s'éteint en chemin : t(d) = exp(−β d) sur un trajet horizontal.
- L'air entre l'objet et l'œil renvoie vers l'œil la lumière du soleil et du ciel : la lumière de l'air. On voit L₀ t + L_air (1 − t).
- Un objet sombre s'éclaircit vers la couleur de l'horizon. Les contrastes baissent tous du même facteur t.
- Koschmieder définit la visibilité : la distance où un objet noir ne garde que 2 % de contraste sur le ciel d'horizon. V = 3,912 / β.
- D'un jour à l'autre, ce sont les aérosols qui changent ; Rayleigh varie peu.

**Les ordres de grandeur.**
- Brouillard sous 1 km, brume humide de 1 à 2 km, brume sèche de 2 à 5 km.
- 23 km : le réglage « clair » usuel du modèle rural de MODTRAN.
- Parcs nationaux américains : 53 à 145 km à l'ouest, 23 à 39 km à l'est.
- Air arctique ou de montagne très pur : jusqu'à 240 km. Limite de Rayleigh : 296 km.
- Épaisseur optique des aérosols à 550 nm, moyenne MODIS : 0,19 sur les terres, 0,13 à 0,14 sur les océans.

**Contraste gardé au sol, sur un trajet horizontal :**

| Visibilité | Mie au sol, km⁻¹ | Fois aujourd'hui | Épaisseur optique, H = 1,2 km | 1 km | 5 km | 10 km | 30 km |
|---|---|---|---|---|---|---|---|
| 217 km, aujourd'hui | 0,004 | 1 | 0,005 | 98 % | 91 % | 84 % | 58 % |
| 60 km | 0,052 | 12 | 0,06 | 94 % | 72 % | 52 % | 14 % |
| 40 km | 0,084 | 19 | 0,10 | 91 % | 61 % | 38 % | 5 % |
| 23 km | 0,157 | 35 | 0,19 | 84 % | 43 % | 18 % | 1 % |

- **Le premier plan reste net :** à 40 km de visibilité, un objet à 300 m ne prend que 3 % de voile.
- **Les plans se séparent :** des crêtes à 2, 5, 10 et 20 km prennent 18, 39, 62 et 86 % de voile. Aujourd'hui : 3, 9, 17 et 30 %.
- **Tout l'éclairage suit :** soleil direct un peu plus faible, ciel plus clair, ombres plus claires et plus bleues, couchers plus orangés. C'est attendu, et voulu.

**Qui le fait, et comment.**
- **Unreal 5, Sky Atmosphere :** la méthode de Hillaire 2020. Sa doc précise que la Mie est « en soi un brouillard en hauteur ». Ses valeurs par défaut sont les nôtres ; les scènes y ajoutent l'Exponential Height Fog pour avoir de la brume.
- **Frostbite 2016 :** même modèle. Le coefficient de Mie y « dépend de l'état de l'atmosphère » : pureté, pollution, poussière. Un brouillard en hauteur s'y ajoute, coloré par la table à l'horizon.
- **Decima, pour Death Stranding :** un brouillard en hauteur analytique, à une seule hauteur d'échelle, éclairé par le soleil et le ciel des tables. Deux jeux de tables, temps clair et brouillard dense, mélangés selon la météo.
- **Ghost of Tsushima :** tables de Rayleigh et de Mie, plus un volume de brume de 128 × 64 × 64 cellules, de 10 cm à 100 km.
- **Flight Simulator :** la brume suit la visibilité des bulletins METAR. En 2024, la diffusion est refaite en lancer de rayons, brouillard, nuages et brume ensemble.
- **Hoffman et Preetham 2002 :** l'origine dans le jeu vidéo, extinction et lumière de l'air d'une densité constante.

**Paramètres proposés.**
- **Un seul réglage, `VISIBILITY_KM`,** la visibilité au niveau de la mer. L'extinction de Mie s'en déduit : 3,912 / V, moins Rayleigh à 550 nm. La diffusion en garde 90 %, comme aujourd'hui.
- **Départ : 40 km,** soit une épaisseur optique de 0,10. Plage plausible : 23 à 60 km. La valeur finale vient du banc.
- **Les tables du démarrage prennent plus de pas :** une couche mince et dense le demande, et ce coût n'est payé qu'une fois.

**Mesure.**
- **Le voile, par les pixels sombres :** dans chaque tranche de distance, le 2ᵉ centile de luminance, rapporté au ciel d'horizon de la même image, vaut à peu près 1 − t(d). C'est l'idée du canal sombre de He et al. On en tire β, donc V.
- **Les moyennes par tranche de distance,** comme Kopf et al. 2008 sur des photos recalées sur un modèle de terrain. Leurs courbes s'écartent nettement d'une exponentielle : on compare des courbes, pas un seul β.
- **Les photos à profondeur connue :** GeoPose3K, plus de 3 000 photos de montagne, avec position, champ, orientation et carte de profondeur tirée du terrain. On garde les photos de beau temps.
- **Nos rendus :** il faut la distance de chaque pixel. L'alpha de l'image HDR la porte déjà ; une vue de diagnostic `MYPLANETENGINE_VIEW=distance` suffit.
- **Les mêmes prises que la photo :** caméra à 2 m et 100 m, trois sites, soleil de face et de dos.
- **Critère :** nos courbes dans l'écart interquartile des photos de beau temps.
- **Le banc de qualité à surveiller :** ses rapports d'octaves ne voient pas un voile uniforme, mais le détail relatif baisse à 800 et 3 000 m. Le comparer avec et sans brume.

### 3.2 Des pas qui montrent la moyenne de l'air

**La règle proposée :** un pas d'intégration montre la moyenne de l'air qu'il traverse. C'est la règle du pixel de `principes.md`, appliquée au rayon.
- Pour une densité exponentielle, la moyenne sur un pas est exacte : H (e^(−h₁/H) − e^(−h₂/H)) / (h₂ − h₁), avec h₁ et h₂ les altitudes de ses bouts.
- Pour un petit écart d'altitude, sa série : pas de soustraction de termes presque égaux.
- La source de lumière reste prise au milieu du pas.

**Qui le fait.**
- **Hillaire 2020, code de référence :** 4 à 14 pas selon la longueur du rayon, répartis en carré, serrés près de la caméra.
- **Ghost of Tsushima :** des tranches en progression de 1,2.
- **Red Dead Redemption 2 :** un volume de cellules jusqu'à 160 m, puis un lancer de rayons au-delà.
- Ces répartitions servent une caméra au sol. Vue d'en haut, la brume est au bout du rayon : seule la moyenne exacte vaut à toute altitude.

**Paramètres.** Les 12 et 32 pas actuels ; peut-être moins une fois la moyenne exacte.

**Mesure.**
- **Une référence à 512 pas** contre le calcul courant : caméra à 2 m, 1 km, 10 km, 100 km et 1 000 km ; vers le nadir, à 45° et vers l'horizon.
- **Critère :** moins de 1/255 d'écart après compression.
- **Le banc de descente :** la part du voile au nadir, sans saut de 1 000 km au sol.
- **Les silhouettes sur le ciel :** le terrain, en 12 pas, et le ciel derrière lui, en 32, se raccordent sans liseré.

### 3.3 La couleur du voile, la désaturation

**Physique.**
- La lumière de l'air a la couleur du ciel près de l'horizon : bleue par Rayleigh, blanchie par les aérosols.
- Les objets sombres bleuissent au loin. Les objets clairs, neige et nuages, jaunissent un peu : l'air leur retire du bleu.
- La saturation baisse à mesure que la lumière de l'air domine.
- Les aérosols fins diffusent davantage le bleu. Exposant d'Ångström de 1,2 à 2,5 pour la pollution et les fumées, de 0 à 1,6 pour la poussière (Dubovik et al. 2002).

**Chez nous.** Tout est calculé par longueur d'onde, sauf la Mie, sans couleur : exposant d'Ångström nul, comme dans la démo de Bruneton.

**Qui.** Bruneton prévoit l'exposant d'Ångström dans ses réglages. Les moteurs en temps réel laissent la Mie grise et colorent les brouillards qu'ils ajoutent.

**Paramètres.**
- La Mie en trois canaux, proportionnelle à (λ / 550 nm)^(−α), α vers 1,3 au départ.
- La poussière des déserts, α proche de 0, attendra un air qui varie selon la région, tiré du climat existant.

**Mesure.** La teinte et la chroma CIELAB des pixels sombres et des moyennes, par tranche de distance, sur photos et rendus. La teinte du ciel à l'horizon.

### 3.4 La brume plus claire vers le soleil

**Physique.**
- Les aérosols diffusent surtout vers l'avant. À contre-jour, le voile est clair et chaud ; dos au soleil, plus sombre et plus bleu.
- Autour du soleil, une auréole blanche.
- Mesures AERONET : asymétrie g de 0,68 à 0,69 à 440 nm, de 0,58 à 0,66 à 670 nm, pour la pollution, les fumées et la poussière ; 0,75 sur l'océan (Dubovik et al. 2002). Soit 0,65 à 0,7 à 550 nm.

**Chez nous.** Cornette-Shanks avec g = 0,8, la valeur de Bruneton, de Hillaire et d'Unreal. Un peu trop vers l'avant : une fois la brume dense, elle sera trop sombre dos au soleil.

**Qui.**
- **Ghost of Tsushima :** la Mie reçoit l'ombre du soleil, Rayleigh l'occultation du ciel, car la Mie vient surtout du soleil.
- **Red Dead Redemption 2 :** plusieurs phases de Henyey-Greenstein, d'asymétrie décroissante, pour approcher la diffusion multiple.

**Paramètres.** g vers 0,7, réglé au banc.

**Mesure.**
- Le ciel à 10° au-dessus de l'horizon, à 30°, 90° et 180° du soleil, rapporté au zénith.
- Références : les types de ciel clair du ciel standard CIE, que la bibliothèque Python `colour` calcule ; des photos.
- Sur les photos à profondeur connue : le voile d'une même distance, vers le soleil et dos à lui.

### 3.5 La couche limite, la hauteur de la brume

**Physique.**
- Les aérosols restent dans la couche que le soleil brasse le jour : 1 à 2 km sur les terres, plafonnée par une inversion. La nuit et l'hiver, elle tombe à quelques centaines de mètres.
- CALIOP : plus de la moitié de l'épaisseur optique sous 2 km, sur les douze régions étudiées.
- Vue d'avion : une bande blanche sous l'horizon, au bord net, et un voile égal quand on regarde vers le bas.
- Les sommets qui sortent de la couche se découpent nets sur la brume.

**Chez nous.** Une exponentielle de 1,2 km au-dessus de la mer : pas de sommet de couche, donc pas de bande nette vue d'en haut.

**Qui.**
- **Ghost of Tsushima :** une densité exponentielle et une densité en sigmoïde selon la hauteur, toutes deux intégrables exactement.
- **Unreal :** deux couches exponentielles, chacune avec sa densité, sa décroissance et son décalage.
- **Red Dead Redemption 2 :** un brouillard global en hauteur, plus une carte de 8 × 8 km : hauteur de départ, décroissance, densité, selon la météo et l'heure.
- **Flight Simulator :** selon les joueurs, la brume s'arrête vers 900 m au-dessus du sol, et forme vue d'en haut une tache blanche. Un plafond trop net ou trop bas se voit.

**Paramètres proposés.**
- **Dans `MediumAt`, la brume devient une couche à sommet doux plus un fond faible.**
- **La couche :** densité constante jusqu'à un sommet vers 1,5 à 2 km, puis une descente logistique sur 0,3 à 0,5 km. Son intégrale est exacte, donc la moyenne par pas de 3.2 aussi.
- **Le fond :** une exponentielle de quelques kilomètres, 20 à 30 % de l'épaisseur optique.
- **Hauteur prise au-dessus du sol régional,** fait le 2026-10-25 : le sol de la carte de la planète, lissé sur 10 km d'écart type, `HAZE_GROUND_SCALE_KM`. Un plateau bien plus large que la couche est épaisse fait sa propre couche ; une crête ou une vallée de quelques fois cette épaisseur, non : le sommet de la couche reste de niveau au-dessus d'elles (De Wekker et Kossmann 2015). La brume s'amincit sur les sommets et remplit les vallées.
- **Les tables du démarrage** prennent le sol de la brume en troisième dimension : 25 tranches de 0 à 6 km. Le reste de l'air garde l'altitude au-dessus de la mer.

**Mesure.**
- **Le banc de descente :** le voile vers le nadir, à 60° et à 80° du nadir, de 1 000 km à 10 m. Une courbe sans saut, qui se stabilise au-dessus de la couche.
- **Des photos d'avion et de sommet :** l'épaisseur angulaire de la bande de brume sous l'horizon, la netteté de son bord.
- **Les profils CALIOP,** comme a priori, pas comme cible.

### 3.6 Les ombres portées du relief, le ciel caché des vallées

**Physique.**
- Une pente à l'ombre ne reçoit que le ciel. Le voile devant elle reste le même : sur une surface sombre, il se voit beaucoup plus. Les montagnes bleues des peintres sont surtout leurs faces à l'ombre.
- Chaque crête jette son ombre sur la vallée derrière elle : les plans se découpent en bandes claires et sombres.
- Au fond d'une vallée, les versants cachent une partie du ciel : le fond s'assombrit.

**Chez nous.** Ni ombre portée, ni occultation du ciel par le relief ; seulement les micro-ombres des textures.

**Qui.**
- **Red Dead Redemption 2 :** une carte d'ombre du terrain, par un lancer de rayon sur la carte des hauteurs vers le soleil. 128 × 128 texels, adoucie selon la longueur du rayon. Elle sert au sol et à l'air.
- **Ghost of Tsushima :** la brume prend la visibilité moyenne du ciel comme occultation.

**Paramètres.** Une spec à part, avec les contraintes de nos principes :
- rien ne saute quand le maillage s'affine ;
- l'ombre de ce que le pixel ne voit pas est une part, comme pour la règle des limites.

**Mesure.** Sur des photos de montagne à hauteur de soleil connue : la part d'ombre, et la luminance des faces à l'ombre selon la distance.

### 3.7 Les rayons de soleil, l'air à l'ombre

**Physique.** L'air dans l'ombre d'une montagne ne renvoie plus le soleil : voile plus sombre derrière les crêtes, rayons vers un soleil bas.

**Qui.**
- **Unreal :** un brouillard volumétrique en cellules de l'écran, ombré.
- **Frostbite 2015 :** des cartes d'ombre volumétriques.
- **Red Dead Redemption 2 :** un volume d'ombre près de la caméra, un lancer de rayons au loin, avec l'ombre du terrain.
- **Star Citizen :** annonce des rayons de soleil, sans détail technique publié.

**Coût.** Élevé, et il faut d'abord 3.6.

**Fait, en piste :** la hauteur d'ombre du relief, lue par les pas du rayon de vue, sans attendre 3.6 ; le même champ peut donner l'ombre du sol (`recherche-rayons.md`).

**Mesure.** À contre-jour, soleil bas : la luminance de l'air devant une crête à l'ombre, contre le ciel au-dessus d'elle.

### 3.8 Les brouillards de vallée, la brume au ras du sol

**Physique.** La nuit, l'air froid descend dans les vallées et s'y accumule sous une inversion. Brume et brouillard y restent le matin ; sur l'eau, la brume se lève.

**Qui.**
- **Red Dead Redemption 2 :** sa carte de brouillard fait la brume du matin sur l'eau, qui se dissipe avec l'heure.
- **Unreal :** la seconde couche de brouillard. **Star Citizen :** un brouillard au sol intégré à l'atmosphère.

**Chez nous.** Rien. Il faut une densité relative au fond des vallées, donc une carte du relief lissé autour de la caméra, et une météo.

**Coût.** Moyen à élevé. Signature forte, mais selon l'heure et le temps : avec la météo.

**Mesure.** Photos d'inversions : hauteur du toit de brume au-dessus du fond de vallée.

### 3.9 Les ombres des nuages

- **Physique :** des taches d'ombre à toutes les distances, qui découpent le paysage en plans. Les peintres s'en servent.
- **Qui :** Red Dead Redemption 2, une carte d'ombre des nuages de 768 × 768.
- **Chez nous :** faites avec les nuages du jeu, tracées vers le soleil à chaque pixel de surface (`spec-nuages.md`) ; pas encore dans l'air.

### 3.10 L'exposition

- **Faite le 2026-10-24,** réglée sur l'éclairement, avec une courbe de tons à pied et épaule : `recherche-tons-exposition.md`.
- **Pas un indice de distance,** mais elle décide de la lecture du voile.
- **Une brume réaliste éclaircit l'horizon et le ciel.** L'exposition fixe suffit le jour ; pas au coucher, déjà noté (`log/spec-rendu.md`, étape B).
- **Ghost of Tsushima règle l'exposition sur l'éclairement,** pas sur la luminance : les sols clairs ne font pas assombrir l'image.
- **Plus tard.**

### 3.11 Le voile optique près du soleil

- **Physique :** la diffusion dans l'œil ou l'objectif ajoute un halo autour du soleil et du ciel très clair, et baisse le contraste près de lui (Spencer et al. 1995).
- **Qui :** Unreal, un halo par convolution.
- **Impact faible,** seulement vers le soleil. Après le reste.
- **Fait le 2026-10-24 :** un halo en 1/θ², celui d'un objectif récent, avant la courbe de tons (`recherche-halo.md`). Coupé par défaut ; `MYPLANETENGINE_GLARE` l'active.

### 3.12 Le flou atmosphérique

- **Physique :** la diffusion vers l'avant des aérosols floute un peu les images sur de longs trajets. Son importance est débattue (Kopeika et al.).
- **Notre pixel couvre 1,45 mrad,** 60° sur 720 lignes : ce flou reste en dessous, sauf brume épaisse.
- **La douceur du lointain vient du voile :** l'œil voit mal les détails fins peu contrastés (Campbell et Robson 1968).
- **Pas de filtre de flou.** Il irait contre tout le travail des textures, pour un effet qui vient déjà de 3.1.

### 3.13 La profondeur de champ

- **Notre champ :** 60° en hauteur, 92° en largeur, soit un objectif de 18 à 21 mm en plein format.
- **À f/8, l'hyperfocale est de 1,4 à 1,8 m :** tout est net d'environ 0,8 m à l'infini.
- **L'œil refait sa mise au point** là où il regarde.
- **Un flou sur le lointain fait lire une maquette :** c'est l'effet de bascule et décentrement, expliqué et mesuré par Held et al. 2010.
- **Les bords flous de `cible-cote.jpg`** sont de cet ordre : à ne pas copier.
- **Elle relève de la mise en scène :** cinématiques, mode photo. Pas d'une caméra libre au-dessus d'un paysage.

### 3.14 Le miroitement de chaleur

- **Physique :** la turbulence au ras d'un sol chaud fait trembler l'image sur de longs trajets.
- **Visible surtout au téléobjectif :** ses déviations restent bien sous notre pixel. Les mirages au ras de sols brûlants sont un cas à part.
- **Pas maintenant.**

### 3.15 Le premier plan

- **Ce n'est pas l'air :** à 300 m, il ne voile que 3 %, même à 40 km de visibilité.
- **C'est le gradient de texture, la netteté, la saturation, les petites ombres.** Les textures à toutes les échelles et les micro-ombres le donnent déjà.
- **Manquent :** les ombres portées (3.6) ; les ombres de contact, quand il y aura des objets.

### Le contrôle par la peinture et la photo

- **Léonard de Vinci :** les montagnes lointaines prennent la couleur de l'air ; plus loin, plus bleues et moins définies.
- **Les plans de valeur :** les peintres de paysage pensent en trois ou quatre plans, du premier plan contrasté et chaud au lointain clair et froid.
- **Carlson et sa théorie des angles :** le ciel est le plus clair, puis le sol plat, puis les pentes, puis les verticales. Notre ciel sur le terrain, pondéré par l'orientation, suit déjà cette règle.
- **Les photographes :** le téléobjectif empile les plans et montre le voile ; le polariseur le réduit, car la lumière de l'air est polarisée (Schechner et al. 2003).
- **L'accord avec la physique :** voile, bleuissement, contraste en baisse, plans. Les peintres adoucissent aussi les bords lointains : c'est ce que l'œil perçoit d'un détail peu contrasté, pas un flou de l'air.

## 4. Selon l'altitude

**Une seule règle :** l'air voile selon ce qu'il y a d'air sur le trajet. Les régimes suivants en découlent, sans réglage par altitude.

**Au ras du sol, dans la couche :**
- Les trajets sont horizontaux : le voile croît avec la distance.
- **Premier plan, sous 300 m :** net, saturé, presque sans voile. Le détail et les ombres le portent.
- **Second plan, de 1 à 10 km :** les crêtes se séparent en plans de plus en plus pâles et bleus. C'est le gain principal.
- **Lointain, au-delà de 30 km :** le relief se fond dans un horizon blanchi.

**En montée, dans la couche, jusqu'à 1,5 à 2 km :**
- Vers le bas, les trajets sortent vite de la brume : le sol sous soi reprend du contraste.
- Vers l'horizon, la brume s'épaissit en bande.

**Au-dessus de la couche, de 2 à 15 km :**
- **Le voile dépend de l'angle, plus de la distance :** traverser la couche coûte son épaisseur divisée par le cosinus de l'angle au nadir.
- **Exemple à 10 km d'altitude, épaisseur optique de 0,10,** Rayleigh compris : le sol garde 84 % de son contraste vers le nadir, 70 % à 60° et 36 % à 80° du nadir.
- **D'où le « tout est loin pareil » :** deux points vus sous le même angle ont le même voile, quelle que soit leur distance.
- **À l'horizon, une bande blanche,** nette si la couche a un sommet (3.5). Les sommets qui dépassent restent nets.

**Vers l'orbite, au-delà de 100 km :**
- Les terres prennent un voile blanchâtre, celui de l'épaisseur optique, qui croît vers le limbe.
- C'est la « brume rose vers l'horizon » de `spec-rendu-lointain.md`, piste 3 : à revoir avec la brume réaliste, contre des photos d'orbite.

**Ce que cela demande au calcul :**
- **Que la couche soit vue à toute altitude :** les pas exacts de 3.2. Sinon la brume change en descente.
- **Le banc de descente le vérifie,** comme pour les matériaux : une courbe sans saut.

**Les indices de premier plan qui ne viennent pas de l'air :**
- **Profondeur de champ :** non, à aucune altitude (3.13).
- **Ombres de contact et occultation :** avec les ombres portées et les objets.

## 5. Sources

**Moteurs et jeux**
- Hillaire 2020, *A Scalable and Production Ready Sky and Atmosphere Rendering Technique*, EGSR : [article](https://diglib.eg.org/handle/10.1111/cgf14050), [code de référence](https://github.com/sebh/UnrealEngineSkyAtmosphere).
- Hillaire 2016, *Physically Based Sky, Atmosphere and Cloud Rendering in Frostbite* : [notes de cours](https://media.contentapi.ea.com/content/dam/eacom/frostbite/files/s2016_pbs_frostbite_sky_clouds.pdf).
- Hillaire 2015, *Physically Based and Unified Volumetric Rendering in Frostbite* : [présentation](https://www.ea.com/news/physically-based-unified-volumetric-rendering-in-frostbite), [cours SIGGRAPH 2015](https://advances.realtimerendering.com/s2015/).
- Unreal Engine : [Sky Atmosphere](https://dev.epicgames.com/documentation/en-us/unreal-engine/sky-atmosphere-component-in-unreal-engine), [Exponential Height Fog](https://dev.epicgames.com/documentation/en-us/unreal-engine/exponential-height-fog-in-unreal-engine).
- de Carpentier et Ishiyama 2017, *Decima Engine: Advances in Lighting and AA*, brouillard en hauteur de Death Stranding : [diapositives](https://advances.realtimerendering.com/s2017/DecimaSiggraph2017.pdf).
- Patry 2021, *Lighting, Atmosphere, and Tonemapping in Real-Time Samurai Cinema*, Ghost of Tsushima : [diapositives](https://www.advances.realtimerendering.com/s2021/jpatry_advances2021/index.html).
- Bauer 2019, *Creating the Atmospheric World of Red Dead Redemption 2* : [cours SIGGRAPH 2019](https://advances.realtimerendering.com/s2019/index.htm), fichier `slides_public_release.pptx`.
- Bruneton 2017, *Precomputed Atmospheric Scattering*, nouvelle implémentation : [code](https://github.com/ebruneton/precomputed_atmospheric_scattering), valeurs de Mie dans `atmosphere/demo/demo.cc`.
- Hoffman et Preetham 2002, *Rendering Outdoor Light Scattering in Real Time* : [GDC 2002](https://renderwonk.com/publications/gdc-2002/).
- Flight Simulator 2024, compte rendu d'un stream des développeurs : [msfsaddons](https://msfsaddons.com/2024/09/25/msfs-team-answers-questions-about-msfs-2024-in-latest-developer-livestream) ; la brume et les METAR, selon les joueurs : [forum](https://forums.flightsimulator.com/t/missing-haze-visibility-outside-metar-vicinity/550442).
- Star Citizen, démo de la CitizenCon 2953, source promotionnelle : [overclock3d](https://overclock3d.net/?p=265778).
- **Sans source primaire trouvée :** Outerra ; un exposé de Guerrilla sur l'atmosphère d'Horizon, hors Decima 2017.

**Physique, mesures, données**
- Visibilité, loi de Koschmieder, seuils du brouillard et des brumes, limite de Rayleigh : [Wikipédia, Visibility](https://en.wikipedia.org/wiki/Visibility).
- MODTRAN, modèle rural à 23 km, exemple d'usage : [Sensors 2021, tableau 1](https://pmc.ncbi.nlm.nih.gov/articles/PMC8271715/table/sensors-21-04313-t001).
- Visibilité dans les parcs nationaux américains : [EPA](https://archive.epa.gov/ttn/naaqsimp/web/html/hazefs.html).
- Remer et al. 2008, climatologie MODIS des aérosols : [résumé](https://espo.nasa.gov/aaoe/node/14101).
- Répartition verticale des aérosols par CALIOP, ACP 2021 : [article](https://acp.copernicus.org/articles/21/15309/2021/acp-21-15309-2021.html).
- De Wekker et Kossmann 2015, *Convective Boundary Layer Heights Over Mountainous Terrain—A Review of Concepts*, Frontiers in Earth Science : [article](https://www.frontiersin.org/journals/earth-science/articles/10.3389/feart.2015.00077/full).
- Dubovik et al. 2002, propriétés optiques des aérosols AERONET : [article](https://www.cfa.harvard.edu/hitran/HITRAN2012/Aerosols/papers/dubovik_et_al._(2002).pdf).
- Narasimhan et Nayar 2002, *Vision and the Atmosphere* : [article](https://www.cs.cmu.edu/~ILIM/publications/PDFs/NN-IJCV02.pdf).
- He, Sun et Tang, canal sombre : [article PAMI](https://people.csail.mit.edu/kaiming/publications/pami10dehaze.pdf).
- Kopf et al. 2008, *Deep Photo*, courbes de brume selon la profondeur : [article](https://johanneskopf.de/publications/deep_photo/deep_photo.pdf).
- Brejcha et Čadík 2017, GeoPose3K : [jeu de données](https://cphoto.fit.vutbr.cz/geoPose3K/).
- Ciel standard CIE : [CIE](https://cie.co.at/publications/spatial-distribution-daylight-cie-standard-general-sky-0), [implémentation dans `colour`](https://colour.readthedocs.io/en/latest/_modules/colour/phenomena/sky/cie2003.html).
- Schechner et al. 2003, la brume vue par la polarisation : [article](https://webee.technion.ac.il/~yoav/publications/haze_osa.pdf).
- Flou des aérosols : [Kopeika et al., JOSA A 1995](https://www.doi.org/10.1364/JOSAA.12.000970), [*Aerosol MTF revisited*](https://cris.iucc.ac.il/en/publications/aerosol-mtf-revisited/).
- Spencer et al. 1995, *Physically-Based Glare Effects for Digital Images* : [article](https://en-cg-web.coecis.cornell.edu/pubs/1995/SSZG95.pdf).

**Perception, peinture**
- Campbell et Robson 1968, sensibilité au contraste selon la finesse : [article](https://doi.org/10.1113/jphysiol.1968.sp008574).
- Held et al. 2010, *Using Blur to Affect Perceived Distance and Size* : [article](https://pmc.ncbi.nlm.nih.gov/articles/PMC3088122).
- Léonard de Vinci, carnets, perspective aérienne : [Richter, § 295](https://www.fromoldbooks.org/Richter-NotebooksOfLeonardo/section-6/item-295.html).
- Carlson, théorie des angles : [résumé](https://theartistsroad.net/articles/thecarlsontheoryofangles).
