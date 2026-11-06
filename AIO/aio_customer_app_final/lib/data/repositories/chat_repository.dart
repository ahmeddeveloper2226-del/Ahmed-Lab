import 'dart:io';
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/constants/api_constants.dart';
import '../models/chat_message_model.dart';
import '../services/api_service.dart';

final chatRepositoryProvider = Provider<ChatRepository>((ref) {
  return ChatRepository(apiService: ref.watch(apiServiceProvider));
});

class ChatHistoryPage {
  final List<ChatMessageModel> messages;
  final String? nextCursor;
  ChatHistoryPage({required this.messages, required this.nextCursor});
}

class ChatRepository {
  final ApiService _api;
  ChatRepository({required ApiService apiService}) : _api = apiService;

  Future<ChatHistoryPage> getHistory(String orderId, {String? before}) async {
    final response = await _api.get(
      ApiConstants.chatHistory(orderId),
      queryParameters: {if (before != null) 'before': before},
    );
    final data = response.data as Map<String, dynamic>;
    return ChatHistoryPage(
      messages: (data['messages'] as List).map((e) => ChatMessageModel.fromJson(e)).toList(),
      nextCursor: data['next_cursor'],
    );
  }

  Future<ChatMessageModel> uploadVoiceMessage(String orderId, String filePath, double durationSeconds) async {
    final formData = FormData.fromMap({
      'audio': await MultipartFile.fromFile(filePath),
      'duration_seconds': durationSeconds,
    });
    final response = await _api.dio.post(ApiConstants.chatVoiceMessage(orderId), data: formData);
    return ChatMessageModel.fromJson(response.data);
  }

  /// Full URL for playing a voice message — the backend enforces
  /// participant access on every fetch, so this alone isn't enough to
  /// listen; the Authorization header (added automatically by
  /// ApiService's interceptor) is required too, which is why voice
  /// playback goes through Dio's download rather than a raw network URL.
  String mediaUrl(String messageId) => '${ApiConstants.baseUrl}${ApiConstants.chatMedia(messageId)}';

  Future<File> downloadVoiceMessage(String messageId, String savePath) async {
    await _api.dio.download(ApiConstants.chatMedia(messageId), savePath);
    return File(savePath);
  }
}