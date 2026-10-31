# Nuages : lumière économique

**État, 27 octobre 2026 :** essai écarté après comparaison en vol. L'utilisateur préfère le rendu précédent ; les coefficients et le define de cet essai sont retirés des sources actives. Le temps GPU comparable ne valide pas son aspect.

**Retour :** « C'était mieux avant. » L'éclairage du commit `5b53b81` est rétabli avant l'intégration de `main`.

**Archives locales :** source modifiée, lanceur et palette de cet essai dans `x64/RejectedLighting20261027/` ; captures et binaires ignorés par Git. Les commandes ci-dessous décrivent l'essai retiré, pas le lancement courant.

**Ancien lancement,** par un lanceur jamais versionné ; la base de l'essai est au tag `piste/nuages-planete-spike` :

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/nuages-lumiere.ps1
```

- Départ en survol des cumulus, météo figée, qualité Éco.
- F1 : sommets éclairés ; F2 : montagne enneigée, contrôle de l'exposition ; F3 : nappe.
- F4–F5 : dessous des couches ; F6–F7 : soleil bas et crépuscule ; F8 : cirrus.
- F9 : région dense depuis800 km ; F10–F11 : deux globes ; F12 : ombres sur terre.
- B : opacité ; C : qualité ; Espace : pause météo ; V : vitesse×1/×5 ; O/P : déplacer le soleil.
- `-Temoin` : Planète avant ce changement, avec la même palette de comparaison, les mêmes poses et soleils.
- `-Build -NoLaunch` : compiler la nouvelle variante isolée ; le binaire natif V4 reste requis.
- Variantes héritées : `-Regional`, `-SansOmbres`, `-SansFiltrage`, `-Vue Meteo|Opacite|Ombres` ; leur première préparation demande `-Build`.

**Approximation retenue :**

- Même densité et même temps météo ; même intégration de transmittance de vue et mêmes ombres au sol.
- Réutiliser les quatre échantillons solaires par point éclairé ; aucune direction, aucun pas ni sous-pixel ajouté.
- Conserver la phase directe existante et regrouper les rebonds suivants dans une source diffuse peu directionnelle.
- Source solaire : `soleil × [phase × exp(−τ) + (0,65/π) × exp(−0,35τ)]`, où `τ = 80 × profondeurSolaire` est déjà calculé.
- Source du ciel : `(0,25/π) × irradianceCiel`, depuis la LUT existante, qui comprend déjà la diffusion atmosphérique multiple.
- Intégrer cette source avec le même facteur Beer de vue `1 − exp(−extinction × pas)` ; la transmittance et les poids de profondeur ne dépendent pas de cette source.
- Soleil déjà filtré par l'atmosphère : les teintes du coucher et la disparition du direct la nuit sont conservées.
- Coefficients ajustés pour l'image ; aucun transport physique complet ni conservation globale de l'énergie revendiqués.
- Le rebond local de la neige, du sol ou de la mer vers les nuages reste absent de cet essai.

**Coût :**

- Une lecture de LUT et une exponentielle de moins par point éclairé que l'ancien terme de second ordre.
- Même nombre de rayons de vue, de densités solaires et de traces d'ombres ; mêmes pas et filtrage orbital.
- Le coût déjà élevé du rendu planétaire à quatre sous-rayons reste présent ; cette correction d'éclairage ne le résout pas.
- Comparaisons GPU ponctuelles sur des cadrages identiques ; elles ne constituent pas un budget global ni un banc statistique.

**Témoin et sources :**

- `x64/NuageFrostbitePlaneteTemoin/` :44 fichiers, ressources et sources vérifiés par empreintes ; base `5b53b81`, tag `piste/nuages-planete-spike`.
- Variante activée par `FROSTBITE_EFFICIENT_LIGHTING` dans `CloudFrostbiteOrbit.hlsli` ; la branche sans ce define garde l'ancien calcul.
- Assets Planète, profils et bruits conservés ; exécutables, captures et manifestes du témoin locaux sous `x64/`.
- Nouvelle itération non commitée ; publication et nouveau tag à la prochaine demande.
- [Epic, Volumetric Clouds](https://dev.epicgames.com/documentation/unreal-engine/volumetric-clouds?application_version=4.27) explique le rôle des rebonds et les compensations d'énergie des approximations temps réel ; les coefficients de cet essai ne proviennent pas de cette documentation.
- [NASA, Shades of White](https://science.nasa.gov/earth/earth-observatory/shades-of-white-87125/) fournit une comparaison réelle neige/nuages ; [Met Office](https://weather.metoffice.gov.uk/learn-about/weather/types-of-weather/clouds/why-are-clouds-white) explique leurs variations de blanc et de gris.

**Vérifications :**

- Rendu et variantes opacité compilés par DXC ; avertissement préexistant de `Materials.hlsli`.
- Captures courtes de sommets, bases et orbite ; même soleil et même météo pour les paires ancien/nouveau.
- Opacité à800 km : un pixel diffère de1/255 sur1280×720 ; les autres sont identiques, sous réordonnancement flottant de l'optimiseur.
- Contrôle du terrain enneigé : différence maximale1/255 ; cette vue contient peu de nuages et sert au contrôle de l'exposition.
- Nuages+air ponctuels, ancien puis nouveau :10,90/10,74 ms en survol ;27,68/27,02 ms à800 km. Nouveau dessous des cumulus :8,45 ms. Aucun surcoût observé sur ces points ; gain global non établi.
- Shader compilé complet :275→261 sites d'appels de lecture filtrée,207→193 sites d'exponentielle ; ces comptes statiques incluent les duplications du compilateur et ne donnent pas directement un temps GPU.
- Captures et rapports locaux : `x64/LightPreview/`, `x64/LightPreviewTemoin/`, `x64/LightOpacityNouveau/`, `x64/LightOpacityTemoin/`, `x64/lighting-checks.json`.
- Soleil bas, cirrus et mouvement à juger en vol par l'utilisateur ; pas de banc prolongé.
