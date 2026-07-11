import unittest
import os
import shutil
import tempfile
from unittest import mock
from pathlib import Path

from bot.medical_store import (
    MedicalStore, haversine_distance, pack_embedding, unpack_embedding, cosine_distance,
)


class TestMedicalStore(unittest.TestCase):
    def setUp(self):
        # Créer un répertoire temporaire pour la base SQLite de test
        self.test_dir = tempfile.mkdtemp()
        self.db_path = Path(self.test_dir) / "test_medical.db"
        # Tests hermétiques : pas d'appel réel à l'API d'embeddings
        self._ge_patch = mock.patch("bot.medical_store.get_embedding", return_value=None)
        self._ge_patch.start()
        self.addCleanup(self._ge_patch.stop)
        self.store = MedicalStore(path=self.db_path)

    def tearDown(self):
        try:
            self.store.close()
        except Exception:
            pass
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_haversine_distance(self):
        # Distance entre Paris (48.8566, 2.3522) et Yaoundé (3.8480, 11.5021)
        # Environ 5080 km
        d = haversine_distance(48.8566, 2.3522, 3.8480, 11.5021)
        self.assertGreater(d, 5000)
        self.assertLess(d, 5200)

        # Distance nulle
        d0 = haversine_distance(3.8480, 11.5021, 3.8480, 11.5021)
        self.assertEqual(d0, 0.0)

    def test_upsert_and_get_records(self):
        record = {
            "id": "NCT123456",
            "title": "Clinical Trial on Malaria in Cameroon",
            "source": "clinicaltrials",
            "nct_id": "NCT123456",
            "url": "https://clinicaltrials.gov/study/NCT123456",
            "summary": "Study on malaria efficacy",
            "eligibility_criteria": "Patients over 18",
            "phase": "Phase II",
            "status": "RECRUITING",
            "conditions": "Malaria",
            "sponsor": "WHO",
            "location_name": "Yaounde Central Hospital",
            "city": "Yaounde",
            "country": "Cameroon",
            "latitude": 3.8480,
            "longitude": 11.5021,
            "ai_cheat_sheet": "AI cheat sheet text"
        }
        self.store.upsert_record(record)
        
        # Test de récupération
        retrieved = self.store.get_record("NCT123456")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["title"], "Clinical Trial on Malaria in Cameroon")
        self.assertEqual(retrieved["ai_cheat_sheet"], "AI cheat sheet text")

        # Test recherche par texte
        search_res = self.store.get_records(search="Malaria")
        self.assertEqual(len(search_res), 1)
        self.assertEqual(search_res[0]["id"], "NCT123456")

    def test_geospatial_distance_matching(self):
        # Yaoundé
        rec_yaounde = {
            "id": "NCT_YAOUNDE",
            "title": "Study in Yaounde",
            "source": "clinicaltrials",
            "latitude": 3.8480,
            "longitude": 11.5021,
            "city": "Yaounde",
            "country": "Cameroon",
            "status": "RECRUITING",
            "sponsor": "Hospital"
        }
        # Douala (environ 200km de Yaoundé)
        rec_douala = {
            "id": "NCT_DOUALA",
            "title": "Study in Douala",
            "source": "clinicaltrials",
            "latitude": 4.0500,
            "longitude": 9.7000,
            "city": "Douala",
            "country": "Cameroon",
            "status": "RECRUITING",
            "sponsor": "Hospital"
        }
        # Dakar (environ 3200km de Yaoundé)
        rec_dakar = {
            "id": "NCT_DAKAR",
            "title": "Study in Dakar",
            "source": "clinicaltrials",
            "latitude": 14.7167,
            "longitude": -17.4677,
            "city": "Dakar",
            "country": "Senegal",
            "status": "RECRUITING",
            "sponsor": "Hospital"
        }

        self.store.upsert_record(rec_yaounde)
        self.store.upsert_record(rec_douala)
        self.store.upsert_record(rec_dakar)

        # Recherche depuis Yaoundé dans un rayon de 500km (Yaoundé & Douala éligibles)
        nearby = self.store.get_nearby_studies(3.8480, 11.5021, max_km=500.0)
        self.assertEqual(len(nearby), 2)
        self.assertEqual(nearby[0]["id"], "NCT_YAOUNDE")
        self.assertEqual(nearby[1]["id"], "NCT_DOUALA")

        # Recherche depuis Yaoundé dans un rayon de 4000km (les 3 éligibles)
        all_nearby = self.store.get_nearby_studies(3.8480, 11.5021, max_km=4000.0)
        self.assertEqual(len(all_nearby), 3)

    def test_traditional_plants(self):
        plant = {
            "name": "Artemisia annua",
            "scientific_name": "Artemisia annua",
            "indications": "Malaria, fever",
            "active_compounds": "Artemisinin",
            "references": ["https://pubmed.ncbi.nlm.nih.gov/123"]
        }
        self.store.upsert_plant(plant)

        retrieved = self.store.get_plants(search="Artemisia")
        self.assertEqual(len(retrieved), 1)
        self.assertEqual(retrieved[0]["name"], "Artemisia annua")
        self.assertEqual(retrieved[0]["references"], ["https://pubmed.ncbi.nlm.nih.gov/123"])

    def test_embedding_helpers(self):
        vec = [0.5, -0.25, 1.0]
        blob = pack_embedding(vec)
        self.assertIsInstance(blob, bytes)
        self.assertEqual(len(blob), 12)  # 3 floats x 4 octets
        restored = unpack_embedding(blob)
        self.assertAlmostEqual(restored[0], 0.5, places=6)
        self.assertAlmostEqual(restored[2], 1.0, places=6)
        self.assertIsNone(pack_embedding(None))
        self.assertIsNone(unpack_embedding(None))
        # Distance cosinus : vecteur identique ≈ 0, orthogonal = 1
        self.assertAlmostEqual(cosine_distance(vec, vec), 0.0, places=6)
        self.assertAlmostEqual(cosine_distance([1, 0], [0, 1]), 1.0, places=6)

    def test_semantic_search_sqlite(self):
        # Embeddings déterministes via mock : malaria proche de la requête, cancer éloigné
        v_malaria = [1.0, 0.0, 0.0]
        v_cancer = [0.0, 1.0, 0.0]
        v_query = [0.9, 0.1, 0.0]
        with mock.patch("bot.medical_store.get_embedding") as ge:
            ge.side_effect = lambda text: v_malaria if "Malaria" in text else v_cancer
            self.store.upsert_record({
                "id": "NCT_MALARIA", "title": "Malaria trial", "source": "clinicaltrials",
                "summary": "Malaria efficacy study", "status": "RECRUITING", "sponsor": "WHO",
            })
            self.store.upsert_record({
                "id": "NCT_CANCER", "title": "Cancer trial", "source": "clinicaltrials",
                "summary": "Oncology study", "status": "RECRUITING", "sponsor": "Lab",
            })
            ge.side_effect = lambda text: v_query  # embedding de la requête
            res = self.store.get_records(search="paludisme", limit=5)
        self.assertEqual(len(res), 2)
        self.assertEqual(res[0]["id"], "NCT_MALARIA")
        self.assertIn("semantic_distance", res[0])
        self.assertLess(res[0]["semantic_distance"], res[1]["semantic_distance"])
        # Le blob binaire ne doit pas fuiter vers l'appelant
        self.assertNotIn("embedding", res[0])

    def test_search_without_embedding_falls_back_to_text(self):
        # Sans clé/modèle (mock renvoie None) : la recherche LIKE classique s'applique
        with mock.patch("bot.medical_store.get_embedding", return_value=None):
            self.store.upsert_record({
                "id": "NCT_TXT", "title": "Malaria trial", "source": "clinicaltrials",
                "summary": "Malaria study", "status": "RECRUITING", "sponsor": "WHO",
            })
            res = self.store.get_records(search="Malaria", limit=5)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["id"], "NCT_TXT")
        self.assertNotIn("embedding", res[0])


if __name__ == "__main__":
    unittest.main()
