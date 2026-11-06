import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/ai_chat_model.dart';
import '../services/api_service.dart';

final aiAssistantRepositoryProvider = Provider<AiAssistantRepository>((ref) {
  return AiAssistantRepository(apiService: ref.watch(apiServiceProvider));
});

class AiAssistantRepository {
  final ApiService _api;

  AiAssistantRepository({required ApiService apiService}) : _api = apiService;

  /// [mode] is 'question' or 'order'. [history] is the full conversation so
  /// far as [{role, content}] maps — the backend keeps no state of its own
  /// (see ai_assistant_service.py's module docstring), so every call resends
  /// everything said so far in this chat session.
  Future<AiChatResponse> chat({
    required String mode,
    required List<Map<String, String>> history,
  }) async {
    final response = await _api.post('/ai/chat', data: {
      'mode': mode,
      'messages': history,
    });
    return AiChatResponse.fromJson(response.data);
  }
}