import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../providers/auth_provider.dart';
import '../../screens/splash/splash_screen.dart';
import '../../screens/onboarding/onboarding_screen.dart';
import '../../screens/onboarding/role_selection_screen.dart';
import '../../screens/auth/login_screen.dart';
import '../../screens/auth/phone_entry_screen.dart';
import '../../screens/auth/otp_screen.dart';
import '../../screens/auth/email_verification_screen.dart';
import '../../screens/categories/categories_screen.dart';
import '../../screens/shops/shops_screen.dart';
import '../../screens/products/shop_detail_screen.dart';
import '../../screens/products/product_detail_screen.dart';
import '../../screens/cart/cart_screen.dart';
import '../../screens/checkout/checkout_screen.dart';
import '../../screens/orders/orders_screen.dart';
import '../../screens/orders/order_detail_screen.dart';
import '../../screens/profile/profile_screen.dart';
import '../../screens/profile/help_screen.dart';
import '../../screens/profile/about_screen.dart';
import '../../screens/addresses/addresses_screen.dart';
import '../../screens/addresses/add_address_screen.dart';
import '../../screens/search/search_screen.dart';
import '../../screens/driver/auth/driver_login_screen.dart';
import '../../screens/driver/home/driver_home_screen.dart';
import '../../screens/driver/orders/driver_active_orders_screen.dart';
import '../../screens/driver/orders/driver_order_detail_screen.dart';
import '../../screens/driver/profile/driver_profile_screen.dart';
import '../../data/models/order_model.dart';
import '../../screens/orders/order_tracking_screen.dart';
import '../../screens/chat/chat_screen.dart';
import '../../screens/chat/call_screen.dart';
import '../../screens/prescriptions/prescription_review_screen.dart';
import '../../widgets/navbar/main_shell.dart';
import '../../widgets/navbar/driver_main_shell.dart';
import '../../screens/grocery/shopping_lists_screen.dart';
import '../../screens/grocery/shopping_list_detail_screen.dart';
import '../../screens/grocery/ai_recipe_screen.dart';
import '../../screens/food/meal_builder_screen.dart';
import '../../screens/food/cross_restaurant_meal_builder_screen.dart';
import '../../screens/pharmacy/medications_screen.dart';
import '../../screens/pharmacy/add_medication_screen.dart';
import '../../screens/electronics/compare_products_screen.dart';

final appRouterProvider = Provider<GoRouter>((ref) {
  return GoRouter(
    initialLocation: '/splash',
    refreshListenable: _RouterRefreshNotifier(ref),
    redirect: (context, state) {
      final authState = ref.read(authStateProvider);
      final onboardingOverride = ref.read(onboardingCompleteOverrideProvider);
      final authOverride = ref.read(authenticatedOverrideProvider);
      final roleOverride = ref.read(roleOverrideProvider);

      // Prefer the synchronous override (set the instant sign-in + our
      // backend session creation succeed) over the Firebase-stream-derived
      // value, which can briefly be stale — see authenticatedOverrideProvider.
      final isAuthenticated =
          authOverride ?? (authState.value?.isAuthenticated ?? false);
      // Prefer the synchronous override (set the instant the user finishes
      // onboarding) over the Firebase-stream-derived value, which can be stale.
      final isOnboardingComplete =
          onboardingOverride ?? (authState.value?.isOnboardingComplete ?? false);
      final role = roleOverride ?? (authState.value?.role ?? 'customer');
      final location = state.uri.path;

      // Routes reachable while NOT authenticated (or mid-login).
      final authRoutes = ['/login', '/phone-entry', '/otp', '/onboarding', '/role-selection', '/driver-login'];
      final isAuthRoute = authRoutes.any((r) => location.startsWith(r));
      final isDriverRoute = location.startsWith('/driver');
      // Reachable by either role — not guarded by the cross-role check below.
      final isSharedRoute = location.startsWith('/chat') ||
          location.startsWith('/call') ||
          location.startsWith('/track-order');

      if (!isOnboardingComplete && location != '/onboarding' && location != '/splash') {
        return '/onboarding';
      }

      if (!isAuthenticated && !isAuthRoute && location != '/splash' && location != '/onboarding') {
        return '/role-selection';
      }

      if (isAuthenticated && isAuthRoute) {
        return role == 'driver' ? '/driver/home' : '/categories';
      }

      // Cross-role guard: a stale deep link or back-navigation shouldn't
      // land a driver on customer screens or vice versa. Shared routes
      // (chat/call/tracking) are exempt — both roles use them.
      if (isAuthenticated && role == 'driver' && !isDriverRoute && !isSharedRoute
          && location != '/splash' && !isAuthRoute) {
        return '/driver/home';
      }
      if (isAuthenticated && role == 'customer' && isDriverRoute && !isSharedRoute) {
        return '/categories';
      }

      return null;
    },
    routes: [
      GoRoute(path: '/splash', builder: (context, state) => const SplashScreen()),
      GoRoute(path: '/onboarding', builder: (context, state) => const OnboardingScreen()),
      GoRoute(path: '/role-selection', builder: (context, state) => const RoleSelectionScreen()),
      GoRoute(path: '/login', builder: (context, state) => const LoginScreen()),
      GoRoute(path: '/driver-login', builder: (context, state) => const DriverLoginScreen()),
      GoRoute(path: '/phone-entry', builder: (context, state) => const PhoneEntryScreen()),
      GoRoute(path: '/otp', builder: (context, state) => const OtpScreen()),
      GoRoute(path: '/email-verification', builder: (context, state) => const EmailVerificationScreen()),

      StatefulShellRoute.indexedStack(
        builder: (context, state, navigationShell) => MainShell(navigationShell: navigationShell),
        branches: [
          StatefulShellBranch(routes: [
            GoRoute(path: '/categories', builder: (context, state) => const CategoriesScreen()),
          ]),
          StatefulShellBranch(routes: [
            GoRoute(path: '/search', builder: (context, state) => const SearchScreen()),
          ]),
          StatefulShellBranch(routes: [
            GoRoute(path: '/orders', builder: (context, state) => const OrdersScreen()),
          ]),
          StatefulShellBranch(routes: [
            GoRoute(path: '/profile', builder: (context, state) => const ProfileScreen()),
          ]),
        ],
      ),

      StatefulShellRoute.indexedStack(
        builder: (context, state, navigationShell) => DriverMainShell(navigationShell: navigationShell),
        branches: [
          StatefulShellBranch(routes: [
            GoRoute(path: '/driver/home', builder: (context, state) => const DriverHomeScreen()),
          ]),
          StatefulShellBranch(routes: [
            GoRoute(path: '/driver/orders', builder: (context, state) => const DriverActiveOrdersScreen()),
          ]),
          StatefulShellBranch(routes: [
            GoRoute(path: '/driver/profile', builder: (context, state) => const DriverProfileScreen()),
          ]),
        ],
      ),
      GoRoute(path: '/driver/order/:orderId', builder: (context, state) {
        final orderId = state.pathParameters['orderId']!;
        return DriverOrderDetailScreen(orderId: orderId);
      }),

      GoRoute(path: '/shops/:categoryId', builder: (context, state) {
        final categoryId = state.pathParameters['categoryId']!;
        final categoryName = state.uri.queryParameters['name'] ?? '';
        return ShopsScreen(categoryId: categoryId, categoryName: categoryName);
      }),
      GoRoute(path: '/shop/:shopId', builder: (context, state) {
        final shopId = state.pathParameters['shopId']!;
        return ShopDetailScreen(shopId: shopId);
      }),
      GoRoute(path: '/prescription/:prescriptionId', builder: (context, state) {
        final prescriptionId = state.pathParameters['prescriptionId']!;
        return PrescriptionReviewScreen(prescriptionId: prescriptionId);
      }),
      GoRoute(path: '/product/:productId', builder: (context, state) {
        final productId = state.pathParameters['productId']!;
        return ProductDetailScreen(productId: productId);
      }),
      GoRoute(path: '/grocery/lists', builder: (context, state) => const ShoppingListsScreen()),
      GoRoute(path: '/grocery/lists/:listId', builder: (context, state) {
        return ShoppingListDetailScreen(listId: state.pathParameters['listId']!);
      }),
      GoRoute(path: '/grocery/recipe', builder: (context, state) => const AiRecipeScreen()),
      GoRoute(path: '/shop/:shopId/meal-builder', builder: (context, state) {
        return MealBuilderScreen(shopId: state.pathParameters['shopId']!);
      }),
      GoRoute(path: '/meal-builder/cross-restaurant', builder: (context, state) {
        return const CrossRestaurantMealBuilderScreen();
      }),
      GoRoute(path: '/medications', builder: (context, state) => const MedicationsScreen()),
      GoRoute(path: '/medications/add', builder: (context, state) => const AddMedicationScreen()),
      GoRoute(path: '/compare-products', builder: (context, state) => const CompareProductsScreen()),
      GoRoute(path: '/cart', builder: (context, state) => const CartScreen()),
      GoRoute(path: '/checkout', builder: (context, state) => const CheckoutScreen()),
      GoRoute(path: '/order/:orderId', builder: (context, state) {
        final orderId = state.pathParameters['orderId']!;
        return OrderDetailScreen(orderId: orderId);
      }),
      GoRoute(path: '/addresses', builder: (context, state) => const AddressesScreen()),
      GoRoute(path: '/addresses/add', builder: (context, state) => const AddAddressScreen()),
      GoRoute(path: '/help', builder: (context, state) => const HelpScreen()),
      GoRoute(path: '/about', builder: (context, state) => const AboutScreen()),
      GoRoute(path: '/track-order', builder: (context, state) => OrderTrackingScreen(order: state.extra as OrderResponse)),
      GoRoute(path: '/chat/:orderId', builder: (context, state) {
        final orderId = state.pathParameters['orderId']!;
        final name = state.uri.queryParameters['name'] ?? '';
        return ChatScreen(orderId: orderId, otherPartyName: name);
      }),
      GoRoute(path: '/call/:orderId', builder: (context, state) {
        final orderId = state.pathParameters['orderId']!;
        final name = state.uri.queryParameters['name'] ?? '';
        final incoming = state.uri.queryParameters['incoming'] == 'true';
        return CallScreen(orderId: orderId, otherPartyName: name, isOutgoing: !incoming);
      }),
    ],
  );
});

// Notifies GoRouter to re-run its `redirect` check whenever auth state,
// onboarding-complete, or the authenticated override changes — WITHOUT
// rebuilding the GoRouter object itself (that was the actual bug: a fresh
// GoRouter always resets to initialLocation, causing the "flashes back to
// onboarding/login" glitch you saw). ref.listen here is a side effect only;
// it does not make appRouterProvider itself rebuild.
class _RouterRefreshNotifier extends ChangeNotifier {
  _RouterRefreshNotifier(Ref ref) {
    ref.listen(authStateProvider, (_, __) => notifyListeners());
    ref.listen(onboardingCompleteOverrideProvider, (_, __) => notifyListeners());
    ref.listen(authenticatedOverrideProvider, (_, __) => notifyListeners());
    ref.listen(roleOverrideProvider, (_, __) => notifyListeners());
  }
}