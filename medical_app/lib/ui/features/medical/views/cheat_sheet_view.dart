import 'package:flutter/material.dart';
import 'package:medical_app/data/models/medical_record.dart';

class CheatSheetView extends StatelessWidget {
  final MedicalRecord record;

  const CheatSheetView({super.key, required this.record});

  // Fonction pour générer le lien mailto pré-rempli
  void _sendOutreachEmail(BuildContext context) {
    final nctId = record.nctId ?? record.id;
    final subject = Uri.encodeComponent("Collaboration clinique - Essai $nctId");
    final body = Uri.encodeComponent(
      "Bonjour,\n\n"
      "En tant que praticien de santé, je souhaite obtenir de plus amples informations concernant votre protocole d'essai clinique \"${record.title}\" (NCT ID: $nctId), actuellement mené par ${record.sponsor} à ${record.locationName}.\n\n"
      "Je souhaiterais évaluer l'éligibilité de certains de mes patients pour une éventuelle collaboration scientifique.\n\n"
      "Dans l'attente de votre réponse, je vous prie d'agréer mes sincères salutations.\n\n"
      "Cordialement,\n"
      "Dr."
    );

    final mailtoUrl = "mailto:info@clinicaltrials.gov?subject=$subject&body=$body";
    
    // Dans une vraie application, on utilise package:url_launcher
    // final uri = Uri.parse(mailtoUrl);
    // launchUrl(uri);
    
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: const Text("Email de mise en relation généré !"),
        action: SnackBarAction(
          label: "Copier",
          onPressed: () {
            // Copier dans le presse papier
          },
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final isTrial = record.source == "clinicaltrials";

    return Scaffold(
      backgroundColor: const Color(0xFF0F172A),
      appBar: AppBar(
        title: Text(isTrial ? "🧬 Protocole d'Essai" : "📚 Publication PubMed"),
        backgroundColor: const Color(0xFF1E293B),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Titre de l'étude
            Text(
              record.title,
              style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.white),
            ),
            const SizedBox(height: 12),
            
            // Badge NCT ID ou Source
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: const Color(0xFF0D9488),
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: Text(
                    isTrial ? (record.nctId ?? "ClinicalTrials") : "PubMed Central",
                    style: const TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.bold),
                  ),
                ),
                const SizedBox(width: 8),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: const Color(0xFF334155),
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: Text(
                    record.status,
                    style: const TextStyle(color: Colors.white70, fontSize: 12),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 24),

            // Fiche Mémo IA (Cheat Sheet)
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: const Color(0xFF1E293B),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: const Color(0xFF0D9488).withOpacity(0.3)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Row(
                    children: [
                      Icon(Icons.auto_awesome, color: Color(0xFF0D9488), size: 18),
                      SizedBox(width: 8),
                      Text(
                        "Fiche Synthétique (IA Cheat Sheet)",
                        style: TextStyle(color: Color(0xFF0D9488), fontWeight: FontWeight.bold, fontSize: 14),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  Text(
                    record.aiCheatSheet ?? record.summary,
                    style: const TextStyle(color: Colors.white, fontSize: 13, height: 1.5),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),

            // Informations de contact et Lab
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: const Color(0xFF1E293B),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    "🏥 Laboratoire & Localisation",
                    style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14),
                  ),
                  const SizedBox(height: 12),
                  Text(
                    "Sponsor : ${record.sponsor}",
                    style: const TextStyle(color: Colors.white70, fontSize: 13),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    "Centre de recherche : ${record.locationName}",
                    style: const TextStyle(color: Colors.white70, fontSize: 13),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    "Ville / Pays : ${record.city}, ${record.country}",
                    style: const TextStyle(color: Colors.white70, fontSize: 13),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 32),

            // Bouton de contact
            ElevatedButton.icon(
              onPressed: () => _sendOutreachEmail(context),
              icon: const Icon(Icons.mail_outline_rounded, color: Colors.white),
              label: const Text(
                "Mise en relation en 1 clic",
                style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold, color: Colors.white),
              ),
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF0D9488),
                padding: const EdgeInsets.symmetric(vertical: 16),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
