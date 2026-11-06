import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

final cloudinaryUploadServiceProvider = Provider<CloudinaryUploadService>((ref) {
  return CloudinaryUploadService();
});

/// Uploads images straight to Cloudinary using an UNSIGNED upload preset —
/// no backend involvement, matching how every other image in this app
/// (shop logos, product photos) already lives on Cloudinary. This is the
/// one place in the app that talks to an external image host directly.
///
/// Setup required (one-time, in the Cloudinary dashboard — NOT something
/// this code can do for you):
///   1. Settings → Upload → Upload presets → Add upload preset
///   2. Set Signing Mode to "Unsigned"
///   3. Name it exactly what's in [_uploadPreset] below (or change the
///      constant to match whatever you name it)
///   4. Optionally restrict the preset's allowed formats to jpg/png/heic
///      and set a folder (e.g. "prescriptions/") to keep these organized
///      separately from shop/product images.
///
/// Deliberately uses a fresh Dio() instance rather than ApiService's
/// shared one — that shared client's interceptor unconditionally attaches
/// a Firebase Authorization header to every request, which Cloudinary's
/// API doesn't expect and doesn't need for an unsigned upload.
class CloudinaryUploadService {
  static const _cloudName = 'dhanjaap5';
  static const _uploadPreset = 'wasla_unsigned'; // <- must match your Cloudinary dashboard preset name exactly

  final Dio _dio = Dio();

  /// Returns the uploaded image's secure_url, or throws on failure —
  /// callers should catch and show a friendly "couldn't upload, try again"
  /// message rather than a raw exception.
  Future<String> uploadImage(String filePath) async {
    final formData = FormData.fromMap({
      'file': await MultipartFile.fromFile(filePath),
      'upload_preset': _uploadPreset,
    });

    final response = await _dio.post(
      'https://api.cloudinary.com/v1_1/$_cloudName/image/upload',
      data: formData,
    );

    final url = response.data['secure_url'] as String?;
    if (url == null) {
      throw Exception('Cloudinary did not return an image URL.');
    }
    return url;
  }
}