class ApiConstants {
  ApiConstants._();

  /// Base URL for local development
  /// - iOS Simulator / Desktop: http://127.0.0.1:8000
  /// - Android Emulator: http://10.0.2.2:8000
  static const String baseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://localhost:8000',
  );

  static const Duration connectTimeout = Duration(seconds: 30);
  static const Duration receiveTimeout = Duration(seconds: 30);

  /// Derives the ws:// (or wss://) URL from baseUrl — same host/port, just
  /// a different scheme, since our WebSocket endpoints live on the same
  /// FastAPI server as the REST API.
  static String get wsBaseUrl {
    final uri = Uri.parse(baseUrl);
    final wsScheme = uri.scheme == 'https' ? 'wss' : 'ws';
    return uri.replace(scheme: wsScheme).toString();
  }

  static String trackingWsUrl(String orderId, String token) =>
      '$wsBaseUrl/tracking/$orderId?token=$token';

  static String realtimeWsUrl(String orderId, String token) =>
      '$wsBaseUrl/realtime/$orderId?token=$token';

  // Chat
  static String chatHistory(String orderId) => '/chat/$orderId/messages';
  static String chatVoiceMessage(String orderId) => '/chat/$orderId/voice-message';
  static String chatMedia(String messageId) => '/chat/media/$messageId';
  static const String iceServers = '/calls/ice-servers';

  // Auth
  static const String authSession = '/auth/session';
  static const String authEmailSendCode = '/auth/email/send-code';
  static const String authEmailVerifyCode = '/auth/email/verify-code';

  // Profile
  static const String me = '/me/';
  static const String meAddresses = '/me/addresses';

  // Categories & Shops
  static const String categories = '/categories/';
  static const String shops = '/shops';

  // Products
  static const String products = '/products';
  static const String productsFastPicks = '/products/fast-picks';
  static String categoryFastPicks(String categoryId) => '/categories/$categoryId/fast-picks';
  static const String search = '/search/';

  // Cart & Checkout
  static const String cart = '/cart/';
  static const String checkout = '/checkout';

  // Orders
  static const String orders = '/orders';

  // Prescriptions (pharmacy category only)
  static const String prescriptions = '/prescriptions';
  static String prescriptionDetail(String id) => '/prescriptions/$id';
  static String prescriptionRemoveItem(String prescriptionId, String itemId) =>
      '/prescriptions/$prescriptionId/items/$itemId';
  static String prescriptionApprove(String id) => '/prescriptions/$id/approve';
  static String prescriptionCancel(String id) => '/prescriptions/$id/cancel';

  // Driver
  static const String driverAuthLogin = '/driver/auth/login';
  // No more "available orders" browsing — the backend decides who gets
  // offered what (see driver_assignment_worker.py). This only ever returns
  // offers already made to the calling driver.
  static const String driverOrdersOffers = '/driver/orders/offers';
  static const String driverOrdersActive = '/driver/orders/active';
  static String driverGroupAccept(String deliveryGroupId) => '/driver/orders/group/$deliveryGroupId/accept';
  static String driverGroupDecline(String deliveryGroupId) => '/driver/orders/group/$deliveryGroupId/decline';
  static String driverOrderStatus(String orderId) => '/driver/orders/$orderId/status';
  static String driverOrderDeliveryStage(String orderId) => '/driver/orders/$orderId/delivery-stage';
  static String driverOrderFailure(String orderId) => '/driver/orders/$orderId/failure';
  static const String driverLocation = '/driver/location';
  static const String driverAvailability = '/driver/availability';

  // Headers
  static const String authorization = 'Authorization';
  static const String bearer = 'Bearer';
  static const String contentType = 'Content-Type';
  static const String applicationJson = 'application/json';
}