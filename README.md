# bso-clinical-trials

[![Discord](https://badgen.net/badge/icon/discord?icon=discord&label)](https://discord.gg/TudsqDqTqb)
![license](https://img.shields.io/github/license/dataesr/bso-clinical-trials)
![GitHub release (latest SemVer)](https://img.shields.io/github/v/release/dataesr/bso-clinical-trials)
![Production release](https://github.com/dataesr/bso-clinical-trials/actions/workflows/build.yml/badge.svg)
[![SWH](https://archive.softwareheritage.org/badge/origin/https://github.com/dataesr/bso-clinical-trials)](https://archive.softwareheritage.org/browse/origin/?origin_url=https://github.com/dataesr/bso-clinical-trials)


## Release

It uses [semver](https://semver.org/).

To create a new release:
```shell
make release VERSION=X.X.X
```

## Courrier

- Pour générer les données, voir notebook/DataGeneration2.ipynb
- Les outputs sont dans le dossier publipostage2.
- Pour exclure un promoteur, ajouter son ROR à la liste "excluded_rors" dans la seconde cellule.
- Pour ajouter un nouveau promoteur, ajouter son ou ses nom(s) dans le fichier bsoclinicaltrials/server/main/bso-lead-sponsors-mapping.csv.