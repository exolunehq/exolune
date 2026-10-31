# Historique du rendu lointain

**Les correctifs de la passe de relief des matériaux,** sortis de `../spec-rendu-lointain.md`, « Corrections faites en chemin », le 2026-10-30, quand la passe a quitté le moteur, commit `3a4508a`. Elle reste au tag `piste/parois-gradins`, où elle est active ; sa spec est `spec-relief-reel.md`. L'état présent est dans `../spec-rendu-lointain.md`.

- **Ailerons dans les éboulis, de près :** dans la passe de relief, la normale entre voisins immédiats variait d'un sommet à l'autre, et les choix qu'elle commande, roche ou non et plan de projection, faisaient sauter le relief d'un mètre. La passe prend maintenant la normale sur quatre mailles de chaque côté. Pas reproduit sur nos sites : à vérifier en vol.
- **Relief des sommets plus loin :** il est porté jusqu'aux mailles de 8 m, au lieu de 1 m, pour que corniches et couloirs apparaissent plus tôt à l'approche. Coût et tremblement inchangés.
