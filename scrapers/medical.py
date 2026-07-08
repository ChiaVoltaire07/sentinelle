"""Scraper médical : ClinicalTrials.gov (API v2) et PubMed (E-Utilities NCBI)."""
from __future__ import annotations

import logging
import hashlib
from typing import List, Dict, Optional
import requests

from scrapers.base import BaseScraper
from bot.config import REQUEST_TIMEOUT

log = logging.getLogger(__name__)

# Coordonnées géographiques par défaut pour les principales villes d'Afrique
CITY_COORDINATES = {
    "yaounde": (3.8480, 11.5021),
    "yaoundé": (3.8480, 11.5021),
    "douala": (4.0500, 9.7000),
    "dakar": (14.7167, -17.4677),
    "abidjan": (5.3600, -4.0083),
    "kinshasa": (-4.4419, 15.2663),
    "libreville": (0.4162, 9.4673),
    "brazzaville": (-4.2634, 15.2832),
    "lomé": (6.1375, 1.2123),
    "lome": (6.1375, 1.2123),
    "cotonou": (6.3703, 2.4253),
    "ouagadougou": (12.3686, -1.5271),
    "bamako": (12.6392, -8.0029),
    "conakry": (9.5370, -13.6773),
    "niamey": (13.5116, 2.1254),
    "lagos": (6.5244, 3.3792),
    "abuja": (9.0765, 7.3986),
    "nairobi": (-1.2921, 36.8219),
    "johannesburg": (-26.2041, 28.0473),
    "carthage": (36.8520, 10.3300),
    "tunis": (36.8065, 10.1815),
    "alger": (36.7538, 3.0588),
    "rabat": (34.0209, -6.8416),
    "casablanca": (33.5731, -7.5898),
    "le caire": (30.0444, 31.2357),
    "cairo": (30.0444, 31.2357),
    "bangui": (4.3947, 18.5582),
    "ndjamena": (12.1348, 15.0557),
    "n'djamena": (12.1348, 15.0557),
    "malabo": (3.7504, 8.7371),
    "kampala": (0.3476, 32.5825),
    "kigali": (-1.9441, 30.0619),
    "lusaka": (-15.3875, 28.3228),
    "accra": (5.6037, -0.1870),
    "addis ababa": (9.0320, 38.7469),
    "addis-abeba": (9.0320, 38.7469),
}


class MedicalScraper(BaseScraper):
    name = "medical"

    def geocode_city(self, city_name: Optional[str]) -> tuple[Optional[float], Optional[float]]:
        """Retourne approximativement latitude/longitude pour les villes africaines."""
        if not city_name:
            return None, None
        c = city_name.lower().strip()
        return CITY_COORDINATES.get(c, (None, None))

    def scrape_clinical_trials(self, term: str, location: Optional[str] = None) -> List[dict]:
        """Interroge ClinicalTrials.gov API v2 pour un terme donné et une localisation."""
        # Exemple: https://clinicaltrials.gov/api/v2/studies?query.term=sickle+cell&query.locn=Cameroon
        url = f"https://clinicaltrials.gov/api/v2/studies?query.term={term}"
        if location:
            url += f"&query.locn={location}"
        url += "&pageSize=15"
        
        log.info("[medical] Scraping ClinicalTrials : %s", url)
        try:
            resp = requests.get(url, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            studies = data.get("studies", [])
            out = []
            
            for s in studies:
                protocol = s.get("protocolSection", {})
                ident = protocol.get("identificationModule", {})
                desc = protocol.get("descriptionModule", {})
                elig = protocol.get("eligibilityModule", {})
                sponsor_mod = protocol.get("sponsorCollaboratorsModule", {})
                status_mod = protocol.get("statusModule", {})
                contacts_mod = protocol.get("contactsLocationsModule", {})
                conditions_mod = protocol.get("conditionsModule", {})
                
                nct_id = ident.get("nctId", "")
                title = ident.get("officialTitle") or ident.get("briefTitle") or "Essai sans titre"
                summary = desc.get("briefSummary", "Aucune description.")
                criteria = elig.get("eligibilityCriteria", "Aucun critère fourni.")
                phase = ", ".join(protocol.get("designModule", {}).get("phases", [])) or "N/A"
                status = status_mod.get("overallStatus", "UNKNOWN")
                conditions = ", ".join(conditions_mod.get("conditions", []))
                lead_sponsor = sponsor_mod.get("leadSponsor", {}).get("name", "Inconnu")
                
                # Extraction de la première localisation pour cartographie
                locations = contacts_mod.get("locations", [])
                loc_name, city, country = "Non spécifié", "Non spécifié", "Non spécifié"
                lat, lon = None, None
                
                if locations:
                    loc = locations[0]
                    loc_name = loc.get("facility", "Hôpital partenaire")
                    city = loc.get("city", "")
                    country = loc.get("country", "")
                    lat, lon = self.geocode_city(city)

                out.append({
                    "id": nct_id,
                    "title": title,
                    "source": "clinicaltrials",
                    "nct_id": nct_id,
                    "url": f"https://clinicaltrials.gov/study/{nct_id}",
                    "summary": summary,
                    "eligibility_criteria": criteria,
                    "phase": phase,
                    "status": status,
                    "conditions": conditions,
                    "sponsor": lead_sponsor,
                    "location_name": loc_name,
                    "city": city,
                    "country": country,
                    "latitude": lat,
                    "longitude": lon,
                    "ai_cheat_sheet": None
                })
            return out
        except Exception as e:
            log.warning("[medical] Échec scraping ClinicalTrials : %s", e)
            return []

    def scrape_pubmed(self, term: str) -> List[dict]:
        """Interroge PubMed via NCBI E-Utilities."""
        # 1. Search ids
        search_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={term}&retmode=json&retmax=10"
        log.info("[medical] Recherche PubMed : %s", search_url)
        try:
            resp = requests.get(search_url, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            id_list = data.get("esearchresult", {}).get("idlist", [])
            if not id_list:
                return []
                
            # 2. Fetch summaries
            ids_str = ",".join(id_list)
            summary_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={ids_str}&retmode=json"
            resp = requests.get(summary_url, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            summary_data = resp.json()
            results = summary_data.get("result", {})
            out = []
            
            for pid in id_list:
                doc = results.get(pid, {})
                title = doc.get("title", "Article sans titre")
                pub_date = doc.get("pubdate", "N/A")
                source = doc.get("source", "PubMed Journal")
                authors = ", ".join([a.get("name", "") for a in doc.get("authors", [])])
                
                # PubMed esummary ne contient pas le résumé complet, on l'estime
                summary = f"Article scientifique publié dans {source} le {pub_date} par {authors}."
                
                out.append({
                    "id": f"pubmed_{pid}",
                    "title": title,
                    "source": "pubmed",
                    "nct_id": None,
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{pid}/",
                    "summary": summary,
                    "eligibility_criteria": None,
                    "phase": "Publication",
                    "status": "COMPLETED",
                    "conditions": term,
                    "sponsor": source,
                    "location_name": source,
                    "city": "Afrique",
                    "country": "Afrique",
                    "latitude": None,
                    "longitude": None,
                    "ai_cheat_sheet": None
                })
            return out
        except Exception as e:
            log.warning("[medical] Échec scraping PubMed : %s", e)
            return []

    def scrape_pubmed_for_plant(self, scientific_name: str) -> List[str]:
        """Recherche sur PubMed les 3 derniers articles scientifiques concernant une plante et retourne leurs URLs."""
        search_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={scientific_name}&retmode=json&retmax=3"
        try:
            resp = requests.get(search_url, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            id_list = data.get("esearchresult", {}).get("idlist", [])
            return [f"https://pubmed.ncbi.nlm.nih.gov/{pid}/" for pid in id_list]
        except Exception as e:
            log.warning("[medical] Échec de la recherche de publications pour la plante %s : %s", scientific_name, e)
            return []
