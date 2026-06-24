import unittest
import os
import shutil
import tempfile
from pathlib import Path

from bot.store import Store


class TestStore(unittest.TestCase):
    def setUp(self):
        # Créer un répertoire temporaire pour la base SQLite de test
        self.test_dir = tempfile.mkdtemp()
        self.db_path = Path(self.test_dir) / "test_scrapper.db"
        self.store = Store(path=self.db_path)

    def tearDown(self):
        try:
            if hasattr(self.store, "close"):
                self.store.close()
            elif getattr(self.store, "conn", None) is not None:
                self.store.conn.close()
        except Exception:
            pass
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_alerts_crud(self):
        # Ajouter une alerte
        alert_id = self.store.add_alert(
            email="doctor@hospital.org",
            query="malaria",
            category="medical",
            location="Cameroon"
        )
        self.assertIsNotNone(alert_id)
        
        # Récupérer les alertes
        alerts = self.store.get_alerts()
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["id"], alert_id)
        self.assertEqual(alerts[0]["email"], "doctor@hospital.org")
        self.assertEqual(alerts[0]["query"], "malaria")
        self.assertEqual(alerts[0]["category"], "medical")
        self.assertEqual(alerts[0]["location"], "Cameroon")

        # Supprimer l'alerte
        self.store.delete_alert(alert_id)
        alerts_after = self.store.get_alerts()
        self.assertEqual(len(alerts_after), 0)


if __name__ == "__main__":
    unittest.main()
