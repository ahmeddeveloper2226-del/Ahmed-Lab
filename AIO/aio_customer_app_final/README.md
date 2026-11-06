# AIO - All in One (Customer App)

A creative, animation-first Flutter customer app for the AIO multi-vendor marketplace platform.

## Features

- **Creative Animations**: Every screen has motion — fade-slide entrances, scale bounces, pulse effects, shimmer loading, staggered lists, elastic navbar transitions
- **Firebase Auth**: Phone OTP, Google Sign-In, Apple Sign-In
- **Full API Integration**: All customer endpoints from your FastAPI backend
- **State Management**: Flutter Riverpod with clean architecture
- **Multi-step Checkout**: Cart review → Address selection → Paymob payment
- **Order Tracking**: Active orders with live status progress bars
- **RTL Arabic UI**: Fully localized for Egyptian market

## Architecture

```
lib/
├── core/
│   ├── animations/       # Custom animation widgets & constants
│   ├── constants/        # API, app, storage constants
│   ├── theme/            # AppTheme, colors, gradients
│   └── utils/            # Router, extensions, helpers
├── data/
│   ├── models/           # All API models (JSON serializable)
│   ├── repositories/     # Business logic layer
│   └── services/         # API & storage services
├── providers/            # Riverpod state management
├── screens/              # All UI screens
└── widgets/              # Reusable animated widgets
```

## Setup

### 1. Prerequisites
- Flutter SDK >= 3.0.0
- Android Studio / Xcode
- Firebase project configured

### 2. Firebase Setup
```bash
flutterfire configure
```

### 3. Install Dependencies
```bash
cd aio_customer_app
flutter pub get
```

### 4. Generate JSON Models
```bash
flutter pub run build_runner build --delete-conflicting-outputs
```

### 5. Add Cairo Font
Download Cairo font files and place in `assets/fonts/`:
- Cairo-Regular.ttf
- Cairo-Bold.ttf
- Cairo-SemiBold.ttf
- Cairo-Medium.ttf

### 6. Run
```bash
# Android emulator
flutter run

# iOS simulator
flutter run -d ios
```

## Environment Variables

Set `API_BASE_URL` for production:
```bash
flutter run --dart-define=API_BASE_URL=https://your-api.com
```

Default dev URLs:
- Android emulator: `http://10.0.2.2:8000`
- iOS simulator: `http://localhost:8000`

## Screens Built

| Screen | Animations |
|--------|-----------|
| Splash | Elastic logo bounce, gradient animation, staggered text |
| Onboarding | Page transitions, scale bounce icons, expanding dots |
| Login | Gradient background, social button animations |
| Phone Entry | Animated input field, gradient button shadow |
| OTP | 6-digit boxes with elastic entrance, shake on error, countdown |
| Categories | Staggered grid, gradient cards, category color coding |
| Shops List | Staggered list, pull-to-ready, rating badges |
| Shop Detail | Sliver parallax header, product grid with scale bounce add |
| Product Detail | Hero transition, quantity animated switcher, elastic add button |
| Cart | Grouped by shop, swipe-to-delete (Slidable), animated total bar |
| Checkout | Step indicator with gradient progress, animated address cards |
| Orders | Active orders with pulse dot, progress bars, status colors |
| Profile | Gradient header, scale bounce avatar, menu sections |
| Addresses | Staggered list, swipe-to-delete, default badge |
| Search | Animated search bar, category chips with gradient selection |
| Email Verification | Gradient icon, code input with centered styling |

## Custom Navbar

The bottom navigation bar features:
- Elastic scale animation on tab switch
- Selected tab floats up with gradient circle background
- Shadow glow effect on active item
- Cart badge count on home tab

## Next Steps for Production

1. **Add real product images** — replace placeholder icons with `CachedNetworkImage`
2. **Configure Firebase** — add `google-services.json` and `GoogleService-Info.plist`
3. **Set up Google Sign-In** — configure OAuth in Firebase console
4. **Set up Apple Sign-In** — add Sign in with Apple capability
5. **Add push notifications** — FCM for order updates
6. **Add maps tracking** — Google Maps for driver location (Phase 3)
7. **Test on real devices** — iOS and Android physical devices
8. **App Store assets** — screenshots, descriptions, privacy policy

## License

Proprietary - AIO Team

