import 'package:flutter/material.dart';
import 'package:medical_app/data/models/medical_record.dart';
import 'package:medical_app/data/repositories/medical_repository.dart';

class SearchViewModel extends ChangeNotifier {
  final MedicalRepository _repository;

  SearchViewModel({required MedicalRepository repository}) : _repository = repository;

  List<MedicalRecord> _records = [];
  List<MedicalRecord> get records => _records;

  bool _isLoading = false;
  bool get isLoading => _isLoading;

  String? _errorMessage;
  String? get errorMessage => _errorMessage;

  String _searchQuery = "";
  String get searchQuery => _searchQuery;

  String _selectedSource = "all"; // 'all', 'clinicaltrials', 'pubmed'
  String get selectedSource => _selectedSource;

  String? _selectedCity; // 'yaounde', 'douala', etc.
  String? get selectedCity => _selectedCity;

  double _radius = 1000.0;
  double get radius => _radius;

  final Map<String, Map<String, double>> citiesCoordinates = {
    "yaounde": {"lat": 3.8480, "lon": 11.5021},
    "douala": {"lat": 4.0500, "lon": 9.7000},
    "dakar": {"lat": 14.7167, "lon": -17.4677},
    "abidjan": {"lat": 5.3600, "lon": -4.0083},
    "kinshasa": {"lat": -4.4419, "lon": 15.2663},
    "lome": {"lat": 6.1375, "lon": 1.2123},
    "nairobi": {"lat": -1.2921, "lon": 36.8219},
  };

  void updateSearchQuery(String query) {
    _searchQuery = query;
  }

  void selectSource(String source) {
    _selectedSource = source;
    loadRecords();
  }

  void selectCity(String? city) {
    _selectedCity = city;
    loadRecords();
  }

  void updateRadius(double newRadius) {
    _radius = newRadius;
    if (_selectedCity != null) {
      loadRecords();
    }
  }

  Future<void> loadRecords() async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      if (_selectedCity != null && citiesCoordinates.containsKey(_selectedCity)) {
        final coords = citiesCoordinates[_selectedCity]!;
        _records = await _repository.searchNearby(
          lat: coords["lat"]!,
          lon: coords["lon"]!,
          maxKm: _radius,
        );
      } else {
        _records = await _repository.searchRecords(
          search: _searchQuery,
          source: _selectedSource,
        );
      }
    } catch (e) {
      _errorMessage = e.toString();
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }
}
