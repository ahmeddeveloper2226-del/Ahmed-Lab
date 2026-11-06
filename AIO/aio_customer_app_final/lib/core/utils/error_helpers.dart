import 'package:dio/dio.dart';

/// Turns any caught exception into a short, friendly Arabic message safe to
/// show directly in the UI — never the raw exception text.
///
/// Found during review: several screens (checkout, cart, order detail,
/// search, prescriptions, chat, driver order detail) were interpolating
/// the caught error directly into a Text widget — `'Error: $err'` or
/// `'تعذر تحميل الطلب: $e'`. For a DioException that renders something
/// like `DioException [connection timeout]: The request connection took
/// longer than 0:00:15.000000 and it was cancelled` — raw English
/// technical detail shown to an Arabic-speaking user on, in one case,
/// the CHECKOUT screen. This is the single place that decides what an
/// error looks like to the user; call this instead of `err.toString()`
/// or `'$err'` anywhere a caught exception reaches a Text/SnackBar.
String friendlyErrorMessage(Object error) {
  if (error is DioException) {
    switch (error.type) {
      case DioExceptionType.connectionTimeout:
      case DioExceptionType.sendTimeout:
      case DioExceptionType.receiveTimeout:
        return 'الاتصال بطيء جدًا الآن، حاول مرة أخرى.';
      case DioExceptionType.connectionError:
        return 'تحقق من اتصالك بالإنترنت وحاول مرة أخرى.';
      case DioExceptionType.badResponse:
        // The backend already sends a friendly Arabic `detail` message on
        // every HTTPException it raises (see the *_router.py files) —
        // prefer that over a generic message when it's actually there.
        final detail = error.response?.data is Map ? error.response?.data['detail'] : null;
        if (detail is String && detail.trim().isNotEmpty) {
          return detail;
        }
        final statusCode = error.response?.statusCode;
        if (statusCode == 401 || statusCode == 403) {
          return 'انتهت صلاحية الجلسة، الرجاء تسجيل الدخول مرة أخرى.';
        }
        if (statusCode != null && statusCode >= 500) {
          return 'حدث خطأ في الخادم، حاول مرة أخرى بعد قليل.';
        }
        return 'تعذر إتمام العملية، حاول مرة أخرى.';
      case DioExceptionType.cancel:
        return 'تم إلغاء العملية.';
      case DioExceptionType.badCertificate:
      case DioExceptionType.unknown:
        return 'تعذر الاتصال بالخادم، تحقق من الإنترنت وحاول مرة أخرى.';
      case DioExceptionType.transformTimeout:
        // TODO: Handle this case.
        throw UnimplementedError();
    }
  }
  return 'حدث خطأ غير متوقع، حاول مرة أخرى.';
}
