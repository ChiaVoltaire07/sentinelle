import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:medical_app/ui/features/medical/view_models/search_view_model.dart';
import 'package:medical_app/ui/features/medical/views/cheat_sheet_view.dart';
import 'package:medical_app/data/models/medical_record.dart';

class SearchView extends StatefulWidget {
  const SearchView({super.key});

  @override
  State<SearchView> createState() => _SearchViewState();
}

class _SearchViewState extends State<SearchView> {
  final _searchController = TextEditingController();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      Provider.of<SearchViewModel>(context, listen: false).loadRecords();
    });
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final viewModel = Provider.of<SearchViewModel>(context);

    return Scaffold(
      backgroundColor: const Color(0xFF0F172A),
      appBar: AppBar(
        title: const Text("🏥 Décision Clinique B2B"),
        backgroundColor: const Color(0xFF1E293B),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded),
            onPressed: () => viewModel.loadRecords(),
          )
        ],
      ),
      body: Column(
        children: [
          // Barre de recherche et filtres
          Container(
            padding: const EdgeInsets.all(16.0),
            color: const Color(0xFF1E293B),
            child: Column(
              children: [
                TextField(
                  controller: _searchController,
                  style: const TextStyle(color: Colors.white),
                  onChanged: viewModel.updateSearchQuery,
                  decoration: InputDecoration(
                    hintText: "Rechercher une pathologie (ex: malaria)...",
                    hintStyle: const TextStyle(color: Colors.white54),
                    prefixIcon: const Icon(Icons.search_rounded, color: Colors.white70),
                    suffixIcon: IconButton(
                      icon: const Icon(Icons.send_rounded, color: Color(0xFF0D9488)),
                      onPressed: () => viewModel.loadRecords(),
                    ),
                    filled: true,
                    fillColor: const Color(0xFF0F172A),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(10),
                      borderSide: BorderSide.none,
                    ),
                  ),
                ),
                const SizedBox(height: 12),
                
                // Filtre de type
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    _buildFilterChip(viewModel, "Tout", "all"),
                    _buildFilterChip(viewModel, "🧬 Essais", "clinicaltrials"),
                    _buildFilterChip(viewModel, "📚 PubMed", "pubmed"),
                  ],
                ),
                const SizedBox(height: 12),
                
                // Filtre géographique
                Row(
                  children: [
                    const Icon(Icons.location_on_outlined, color: Color(0xFF0D9488), size: 20),
                    const SizedBox(width: 8),
                    Expanded(
                      child: DropdownButton<String>(
                        dropdownColor: const Color(0xFF1E293B),
                        value: viewModel.selectedCity,
                        hint: const Text("Distance par rapport à...", style: TextStyle(color: Colors.white70, fontSize: 13)),
                        style: const TextStyle(color: Colors.white, fontSize: 13),
                        isExpanded: true,
                        underline: Container(height: 1, color: Colors.white24),
                        items: const [
                          DropdownMenuItem(value: null, child: Text("Aucun filtre géographique")),
                          DropdownMenuItem(value: "yaounde", child: Text("Yaoundé (Cameroun)")),
                          DropdownMenuItem(value: "douala", child: Text("Douala (Cameroun)")),
                          DropdownMenuItem(value: "dakar", child: Text("Dakar (Sénégal)")),
                          DropdownMenuItem(value: "abidjan", child: Text("Abidjan (Côte d'Ivoire)")),
                          DropdownMenuItem(value: "kinshasa", child: Text("Kinshasa (RDC)")),
                          DropdownMenuItem(value: "nairobi", child: Text("Nairobi (Kenya)")),
                        ],
                        onChanged: viewModel.selectCity,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),

          // Liste des résultats
          Expanded(
            child: viewModel.isLoading
                ? const Center(child: CircularProgressIndicator(color: Color(0xFF0D9488)))
                : viewModel.errorMessage != null
                    ? Center(
                        child: Padding(
                          padding: const EdgeInsets.all(24.0),
                          child: Text(
                            viewModel.errorMessage!,
                            style: const TextStyle(color: Colors.redAccent),
                            textAlign: TextAlign.center,
                          ),
                        ),
                      )
                    : viewModel.records.isEmpty
                        ? const Center(
                            child: Text(
                              "Aucun résultat trouvé.\nEntrez un mot-clé ou modifiez les filtres.",
                              style: TextStyle(color: Colors.white60),
                              textAlign: TextAlign.center,
                            ),
                          )
                        : ListView.builder(
                            padding: const EdgeInsets.all(12),
                            itemCount: viewModel.records.length,
                            itemBuilder: (context, index) {
                              final record = viewModel.records[index];
                              return _buildRecordCard(context, record);
                            },
                          ),
          ),
        ],
      ),
    );
  }

  Widget _buildFilterChip(SearchViewModel viewModel, String label, String value) {
    final active = viewModel.selectedSource == value;
    return GestureDetector(
      onTap: () => viewModel.selectSource(value),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        decoration: BoxDecoration(
          color: active ? const Color(0xFF0D9488) : const Color(0xFF0F172A),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: active ? Colors.transparent : Colors.white24),
        ),
        child: Text(
          label,
          style: TextStyle(color: active ? Colors.white : Colors.white70, fontSize: 13, fontWeight: FontWeight.w600),
        ),
      ),
    );
  }

  Widget _buildRecordCard(BuildContext context, MedicalRecord record) {
    final isTrial = record.source == "clinicaltrials";
    
    return Card(
      color: const Color(0xFF1E293B),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
      margin: const EdgeInsets.only(bottom: 12),
      child: ListTile(
        contentPadding: const EdgeInsets.all(12),
        leading: Icon(
          isTrial ? Icons.science_outlined : Icons.menu_book_rounded,
          color: isTrial ? const Color(0xFF38BDF8) : const Color(0xFF34D399),
          size: 32,
        ),
        title: Text(
          record.title,
          maxLines: 2,
          overflow: TextOverflow.ellipsis,
          style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14),
        ),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const SizedBox(height: 6),
            Text(
              "Sponsor : ${record.sponsor}",
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(color: Colors.white70, fontSize: 12),
            ),
            const SizedBox(height: 4),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  isTrial ? "Phase : ${record.phase}" : "Publication",
                  style: const TextStyle(color: Colors.white60, fontSize: 11),
                ),
                if (record.distanceKm != null)
                  Text(
                    "📍 ${record.distanceKm!.toStringAsFixed(1)} km",
                    style: const TextStyle(color: Color(0xFF0D9488), fontWeight: FontWeight.bold, fontSize: 12),
                  ),
              ],
            ),
          ],
        ),
        onTap: () {
          Navigator.push(
            context,
            MaterialPageRoute(
              builder: (_) => CheatSheetView(record: record),
            ),
          );
        },
      ),
    );
  }
}
