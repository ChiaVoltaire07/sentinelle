import 'package:flutter/material.dart';
import 'package:medical_app/data/services/api_service.dart';

class LoginViewModel extends ChangeNotifier {
  final ApiService apiService;

  LoginViewModel({required this.apiService});

  bool _isLoading = false;
  bool get isLoading => _isLoading;

  String? _errorMessage;
  String? get errorMessage => _errorMessage;

  Future<bool> authenticate(String email, String licenseNumber, String password) async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    if (email.isEmpty || licenseNumber.isEmpty || password.isEmpty) {
      _errorMessage = "Tous les champs sont obligatoires.";
      _isLoading = false;
      notifyListeners();
      return false;
    }

    if (licenseNumber.length < 5) {
      _errorMessage = "Numéro d'enregistrement professionnel invalide.";
      _isLoading = false;
      notifyListeners();
      return false;
    }

    try {
      await apiService.login(
        email: email,
        password: password,
        licenseNumber: licenseNumber,
      );
      _isLoading = false;
      notifyListeners();
      return true;
    } catch (e) {
      // Fallback inscription si le compte n'existe pas encore
      try {
        await apiService.register(
          email: email,
          password: password,
          licenseNumber: licenseNumber,
        );
        _isLoading = false;
        notifyListeners();
        return true;
      } catch (e2) {
        _errorMessage = e2.toString().replaceFirst('Exception: ', '');
        _isLoading = false;
        notifyListeners();
        return false;
      }
    }
  }
}
