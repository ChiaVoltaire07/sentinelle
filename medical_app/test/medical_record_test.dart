import 'package:flutter_test/flutter_test.dart';
import 'package:medical_app/data/models/medical_record.dart';

void main() {
  test('MedicalRecord.fromJson parse basique', () {
    final record = MedicalRecord.fromJson({
      'id': 'NCT1',
      'title': 'Malaria study',
      'source': 'clinicaltrials',
      'nct_id': 'NCT1',
      'url': 'https://example.com',
      'summary': 'Summary',
      'phase': 'PHASE2',
      'status': 'RECRUITING',
      'conditions': 'Malaria',
      'sponsor': 'WHO',
      'location_name': 'Central',
      'city': 'Yaounde',
      'country': 'Cameroon',
      'latitude': 3.84,
      'longitude': 11.50,
      'ai_cheat_sheet': 'memo',
    });
    expect(record.id, 'NCT1');
    expect(record.city, 'Yaounde');
    expect(record.aiCheatSheet, 'memo');
    expect(record.toJson()['nct_id'], 'NCT1');
  });
}
