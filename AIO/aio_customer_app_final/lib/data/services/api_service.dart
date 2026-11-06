import 'package:dio/dio.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/constants/api_constants.dart';
import 'storage_service.dart';

final apiServiceProvider = Provider<ApiService>((ref) {
  final storage = ref.watch(storageServiceProvider);
  return ApiService(storage: storage);
});

class ApiService {
  final StorageService _storage;
  late final Dio _dio;

  ApiService({required StorageService storage}) : _storage = storage {
    _dio = Dio(
      BaseOptions(
        baseUrl: ApiConstants.baseUrl,
        connectTimeout: ApiConstants.connectTimeout,
        receiveTimeout: ApiConstants.receiveTimeout,
        headers: {
          ApiConstants.contentType: ApiConstants.applicationJson,
        },
      ),
    );

    _dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) async {
          // Always ask Firebase for the CURRENT token rather than replaying
          // a string we saved once in SharedPreferences. Firebase ID tokens
          // expire hourly; FirebaseAuth caches this internally and silently
          // refreshes it under the hood when it's near/past expiry, so this
          // call is cheap and correct on every request — no manual renewal
          // logic needed on our side.
          final token = await FirebaseAuth.instance.currentUser?.getIdToken();
          if (token != null) {
            options.headers[ApiConstants.authorization] =
                '${ApiConstants.bearer} $token';
          }
          handler.next(options);
        },
        onError: (error, handler) async {
          final requestOptions = error.requestOptions;
          final alreadyRetried = requestOptions.extra['retried_with_fresh_token'] == true;

          if (error.response?.statusCode == 401 &&
              !alreadyRetried &&
              FirebaseAuth.instance.currentUser != null) {
            try {
              // Force a hard refresh (bypassing Firebase's local cache)
              // in case the cached token was rejected for a reason that
              // isn't plain expiry (clock skew, revocation, etc.), then
              // retry the exact same request once with it.
              final freshToken =
                  await FirebaseAuth.instance.currentUser!.getIdToken(true);
              requestOptions.headers[ApiConstants.authorization] =
                  '${ApiConstants.bearer} $freshToken';
              requestOptions.extra['retried_with_fresh_token'] = true;

              final retryResponse = await _dio.fetch(requestOptions);
              handler.resolve(retryResponse);
              return;
            } catch (_) {
              // Fall through to the original error below — genuinely
              // signed out or the retry failed for its own reason.
            }
          }

          if (error.response?.statusCode == 401) {
            await _storage.clearToken();
          }
          handler.next(error);
        },
      ),
    );
  }

  Dio get dio => _dio;

  Future<Response> get(String path, {Map<String, dynamic>? queryParameters}) async {
    return await _dio.get(path, queryParameters: queryParameters);
  }

  Future<Response> post(String path, {dynamic data}) async {
    return await _dio.post(path, data: data);
  }

  Future<Response> put(String path, {dynamic data}) async {
    return await _dio.put(path, data: data);
  }

  Future<Response> patch(String path, {dynamic data}) async {
    return await _dio.patch(path, data: data);
  }

  Future<Response> delete(String path) async {
    return await _dio.delete(path);
  }
}