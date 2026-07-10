"""Script d'initialisation de la base de données de pharmacopée traditionnelle.

Insère les plantes médicinales africaines les plus étudiées avec leurs indications
et leurs principes actifs.
"""
from __future__ import annotations

import logging
from bot.medical_store import MedicalStore

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("populate_plants")


def populate():
    store = MedicalStore()
    
    plants = [
        {
            "name": "Artemisia annua (Armoise annuelle)",
            "scientific_name": "Artemisia annua",
            "indications": "Paludisme (Malaria), fièvres tropicales, infections parasitaires.",
            "active_compounds": "Artémisinine, flavonoïdes, huiles essentielles.",
            "references": [
                "https://pubmed.ncbi.nlm.nih.gov/26484835/", # Prix Nobel Tu Youyou
                "https://pubmed.ncbi.nlm.nih.gov/30583856/"
            ]
        },
        {
            "name": "Moringa (Néverdier)",
            "scientific_name": "Moringa oleifera",
            "indications": "Malnutrition, hypertension artérielle, diabète de type 2, stimulation immunitaire.",
            "active_compounds": "Isothiocyanates, quercétine, acide chlorogénique, vitamines A/C/E.",
            "references": [
                "https://pubmed.ncbi.nlm.nih.gov/25808201/",
                "https://pubmed.ncbi.nlm.nih.gov/29849202/"
            ]
        },
        {
            "name": "Neem (Margousier)",
            "scientific_name": "Azadirachta indica",
            "indications": "Infections cutanées, états fiévreux, antiparasitaire, soins bucco-dentaires.",
            "active_compounds": "Azadirachtine, nimbin, nimbidol.",
            "references": [
                "https://pubmed.ncbi.nlm.nih.gov/22037986/",
                "https://pubmed.ncbi.nlm.nih.gov/24513456/"
            ]
        },
        {
            "name": "Prunier d'Afrique",
            "scientific_name": "Prunus africana",
            "indications": "Hypertrophie bénigne de la prostate (HBP), troubles urinaires associés.",
            "active_compounds": "Phytostérols (bêta-sitostérol), triterpènes pentacycliques.",
            "references": [
                "https://pubmed.ncbi.nlm.nih.gov/11869581/",
                "https://pubmed.ncbi.nlm.nih.gov/27045431/"
            ]
        },
        {
            "name": "Pervenche de Madagascar",
            "scientific_name": "Catharanthus roseus",
            "indications": "Cancers (Leucémies, lymphomes), régulation de la glycémie.",
            "active_compounds": "Vinblastine, vincristine (alcaloïdes antimitotiques).",
            "references": [
                "https://pubmed.ncbi.nlm.nih.gov/23849501/",
                "https://pubmed.ncbi.nlm.nih.gov/25698421/"
            ]
        },
        {
            "name": "Arbre de sang (Harungana)",
            "scientific_name": "Harungana madagascariensis",
            "indications": "Troubles digestifs, insuffisance pancréatique, cicatrisation des plaies.",
            "active_compounds": "Harunganine, anthraquinones, tannins.",
            "references": [
                "https://pubmed.ncbi.nlm.nih.gov/17562013/",
                "https://pubmed.ncbi.nlm.nih.gov/22145620/"
            ]
        },
        {
            "name": "Kigelia (Saucissonnier)",
            "scientific_name": "Kigelia africana",
            "indications": "Infections cutanées, plaies chroniques, candidoses.",
            "active_compounds": "Iridoïdes, naphtoquinones, flavonoïdes.",
            "references": [
                "https://pubmed.ncbi.nlm.nih.gov/21798328/"
            ]
        },
        {
            "name": "Voacanga",
            "scientific_name": "Voacanga africana",
            "indications": "Troubles neurologiques exploratoires, inflammation.",
            "active_compounds": "Alcaloïdes iboga (voacangine).",
            "references": [
                "https://pubmed.ncbi.nlm.nih.gov/21944564/"
            ]
        },
        {
            "name": "Griffonia",
            "scientific_name": "Griffonia simplicifolia",
            "indications": "Troubles de l'humeur (précurseur 5-HTP), recherche sérotoninergique.",
            "active_compounds": "5-hydroxytryptophane (5-HTP).",
            "references": [
                "https://pubmed.ncbi.nlm.nih.gov/23182186/"
            ]
        },
    ]
    
    log.info("Population de la table traditional_plants...")
    for p in plants:
        store.upsert_plant(p)
    log.info("✅ Pharmacopée traditionnelle initialisée avec succès (%d plantes insérées).", len(plants))


if __name__ == "__main__":
    populate()
