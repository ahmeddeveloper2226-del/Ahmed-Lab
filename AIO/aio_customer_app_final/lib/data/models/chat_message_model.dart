class ChatMessageModel {
  final String id;
  final String orderId;
  final String? senderId;
  final String receiverId;
  final String messageType; // text | voice | system
  final String status; // sent | delivered | read
  final String? content;
  final String? audioUrl;
  final double? audioDurationSeconds;
  final DateTime createdAt;

  ChatMessageModel({
    required this.id,
    required this.orderId,
    required this.senderId,
    required this.receiverId,
    required this.messageType,
    required this.status,
    required this.content,
    required this.audioUrl,
    required this.audioDurationSeconds,
    required this.createdAt,
  });

  factory ChatMessageModel.fromJson(Map<String, dynamic> json) => ChatMessageModel(
        id: json['id'],
        orderId: json['order_id'],
        senderId: json['sender_id'] ?? json['from'],
        receiverId: json['receiver_id'] ?? '',
        messageType: json['message_type'] ?? (json['audio_url'] != null ? 'voice' : 'text'),
        status: json['status'] ?? 'sent',
        content: json['content'],
        audioUrl: json['audio_url'],
        audioDurationSeconds: (json['audio_duration_seconds'] as num?)?.toDouble(),
        createdAt: json['created_at'] != null ? DateTime.parse(json['created_at']) : DateTime.now(),
      );

  ChatMessageModel copyWith({String? status}) => ChatMessageModel(
        id: id,
        orderId: orderId,
        senderId: senderId,
        receiverId: receiverId,
        messageType: messageType,
        status: status ?? this.status,
        content: content,
        audioUrl: audioUrl,
        audioDurationSeconds: audioDurationSeconds,
        createdAt: createdAt,
      );

  bool get isSystem => messageType == 'system';
  bool isMine(String myUid) => senderId == myUid;
}