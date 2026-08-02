import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:medical_app/data/services/api_service.dart';
import 'package:medical_app/data/repositories/medical_repository.dart';
import 'package:medical_app/ui/features/auth/view_models/login_view_model.dart';
import 'package:medical_app/ui/features/medical/view_models/search_view_model.dart';
import 'package:medical_app/ui/features/auth/views/login_view.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final apiService = ApiService();
  await apiService.loadToken();
  runApp(MyApp(apiService: apiService));
}

class MyApp extends StatelessWidget {
  final ApiService apiService;
  const MyApp({super.key, required this.apiService});

  @override
  Widget build(BuildContext context) {
    final medicalRepository = MedicalRepository(apiService: apiService);

    return MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => LoginViewModel(apiService: apiService)),
        ChangeNotifierProvider(
          create: (_) => SearchViewModel(repository: medicalRepository),
        ),
      ],
      child: MaterialApp(
        title: 'Décision Clinique Médicale',
        debugShowCheckedModeBanner: false,
        theme: ThemeData(
          useMaterial3: true,
          brightness: Brightness.dark,
          primaryColor: const Color(0xFF0D9488),
          scaffoldBackgroundColor: const Color(0xFF0F172A),
          appBarTheme: const AppBarTheme(
            backgroundColor: Color(0xFF1E293B),
            elevation: 0,
            titleTextStyle: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.bold,
              color: Colors.white,
            ),
            iconTheme: IconThemeData(color: Colors.white),
          ),
        ),
        home: const LoginView(),
      ),
    );
  }
}
