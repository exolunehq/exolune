# Spécifications techniques et fonctionnelles

## Objectif du moteur

Créer un moteur 3D performant sous DirectX pour un jeu vidéo spatial capable de :

* Afficher une planète en temps réel, de l'espace jusqu'à l'atterrissage à sa surface.
* Générer dynamiquement un terrain détaillé en fonction de la position et de l'orientation de la caméra.

## Fonctionnalités Principales

### Vue Générale

* Transition fluide entre les vues spatiales (vue planétaire distante) et locales (surface détaillée de la planète).

## Génération du terrain planétaire

### Principes de base

* Utilisation d'un mesh plane initiale constituée d'un nombre déterminé de vertices, positionnée à une certaine altitude par rapport au centre orbital de la planète.
* La mèche doit toujours être orientée face à la position caméra afin de maximiser l’efficacité du rendu.

### Méthodologie de génération

* Chaque frame :

  1. Positionner la mesh :

     1. **Positionnement :**

        * Le centre du mesh doit être situé exactement sur la droite reliant le centre de la planète à la caméra.
        * La position du mesh doit se trouver à une distance exacte de **6 378 km** du centre de la planète, soit à la surface terrestre.

     2. **Orientation :**

        * Le mesh doit être orienté selon le plan tangent à la surface de la planète au point déterminé précédemment.
        * L'orientation du mesh doit être perpendiculaire au vecteur reliant le centre de la planète et la caméra (la normale du mesh correspond exactement à ce vecteur).
    
    Implémentation pratique possible :
    1. On positione la mesh au centre de la planète (0,0,0)
    2. On l'oriente simplement pour qu'elle face toujours face à la position de la caméra.
    3. On déplace les coordonées des vertices pour qu'ils soient à 6,378km du centre. Comme on est dans
    l'espace relatif de la mesh, en fait on a juste à élever les vertices (donc on pourrait même le faire avant le point 2 si on voulait)
    4. Enfin on normalize pour sphériser. 

     ### Résumé en termes techniques

     * **Centre du mesh** : Position du point tangent sur la surface de la planète, déterminé par l'intersection de la droite reliant le centre de la planète à la caméra.
     * **Normale du mesh** : Vecteur dirigé du centre de la planète vers la caméra.
     * **Distance exacte** : Rayon terrestre de 6 378 km.

  2. Normaliser les vertices pour obtenir une courbure sphérique naturelle de la mesh.

  3. Subdivision de la mesh

     #### 1. Subdivision adaptative en "toile d'araignée"

     * La subdivision suit un schéma radial, similaire à une toile d'araignée, avec une forte densité de subdivision au centre.
     * La densité de subdivision diminue progressivement à mesure que l'on s'éloigne du centre vers les bords du mesh.

     #### 2. Détermination dynamique du centre de subdivision

     * Le centre de la toile ne correspond pas forcément au centre géométrique du mesh.
     * Le centre est déterminé dynamiquement en temps réel, en fonction de :

       * La position de la caméra par rapport au mesh.
       * Le vecteur de regard (direction du regard) de la caméra.
       * L'intersection entre le vecteur de regard et le mesh (point focal).

     #### 3. Gestion dynamique du niveau de détail

     * Implémentation d'un système de contrôle de détail adaptatif permettant de :

       * Ajuster dynamiquement la densité du maillage autour du point focal.
       * Réduire rapidement la densité loin du point focal afin d'économiser des ressources.
     * Assurer une transition fluide et imperceptible entre les différentes zones de niveaux de détails.

  4. Sélectionner uniquement les vertices visibles par la caméra pour optimisation.

  5. Envoyer les coordonnées des vertices au Compute Shader pour calcul parallèle.

  6. Appliquer des fonctions de bruit cohérent imbriquées (Coherent Noise) pour calculer les élévations de chaque vertice.

  7. Appliquer les élévations aux vertices

  8. Générer un rendu coloré cohérent selon l'élévation (ex : bleu pour eau, marron pour terre, blanc pour neige).

### Optimisation des performances

* Utilisation intensive du GPU via des Compute Shaders (GP-GPU).
* Génération uniquement des vertices visibles pour éviter le gaspillage des ressources GPU.

## Gestion de la Caméra

### Positionnement et mouvement

* Initialement positionnée en orbite proche pour le développement.
* Capacité de se déplacer de façon fluide jusqu’à la surface pour vérifier la cohérence et les performances du rendu en temps réel.

###

## Spécifications techniques générales

### Technologie et environnement

* DirectX (Direct3D) pour le rendu graphique.
* Compute Shader pour calcul parallèle intensif (GPGPU).
* Algorithmes de Coherent Noise imbriqués pour génération procédurale cohérente et réaliste.

### Exigences de performance

* Temps réel avec taux de rafraîchissement fluide (minimum 30-60 FPS).
* Génération et adaptation instantanée des détails à chaque mouvement ou changement de point de vue de la caméra.

## Notes additionnelles

* La génération initiale à échelle cosmique (positionnement de systèmes solaires) est prévue mais sera abordée dans un second temps.
* Ce document est évolutif, devant être enrichi au fur et à mesure de l'avancement technique et des validations intermédiaires.
