import 'package:flutter/material.dart';
import '../../../core/utils/error_helpers.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart' as ll;
import '../../../core/theme/app_theme.dart';
import '../../../core/animations/custom_animations.dart';
import '../../../data/models/driver_order_model.dart';
import '../../../data/services/location_service.dart';
import '../../../data/repositories/driver_repository.dart';
import '../../../providers/driver_provider.dart';

class DriverHomeScreen extends ConsumerStatefulWidget {
  const DriverHomeScreen({super.key});

  @override
  ConsumerState<DriverHomeScreen> createState() => _DriverHomeScreenState();
}

class _DriverHomeScreenState extends ConsumerState<DriverHomeScreen> {
  final MapController _mapController = MapController();
  bool _requestingLocation = true;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _requestLocation());
  }

  Future<void> _requestLocation() async {
    final locationService = ref.read(locationServiceProvider);
    final result = await locationService.getCurrentLocation();

    if (!mounted) return;

    if (result.isSuccess) {
      ref.read(driverPositionProvider.notifier).state = DriverPosition(result.lat!, result.lng!);
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(locationService.failureMessage(result.failure!))),
      );
    }
    setState(() => _requestingLocation = false);
  }

  Future<void> _toggleOnline(bool value) async {
    final position = ref.read(driverPositionProvider);
    ref.read(driverOnlineProvider.notifier).state = value;
    try {
      await ref.read(driverRepositoryProvider).updateAvailability(
            isAvailable: value,
            lat: position?.lat,
            lng: position?.lng,
          );
    } catch (_) {
      if (!mounted) return;
      // Revert on failure so the toggle reflects what the backend actually has.
      ref.read(driverOnlineProvider.notifier).state = !value;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('تعذر تحديث حالتك، حاول مرة أخرى.')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final position = ref.watch(driverPositionProvider);
    final isOnline = ref.watch(driverOnlineProvider);
    final offersAsync = ref.watch(driverOffersProvider);

    return Scaffold(
      body: Stack(
        children: [
          // --- Map ---------------------------------------------------------
          if (position != null)
            FlutterMap(
              mapController: _mapController,
              options: MapOptions(
                initialCenter: ll.LatLng(position.lat, position.lng),
                initialZoom: 13,
              ),
              children: [
                // Dev-friendly default tile source. OpenStreetMap's own
                // servers explicitly ask production apps not to hit them
                // directly at real traffic volumes — swap this urlTemplate
                // for a proper provider (MapTiler/Stadia Maps/Carto all
                // have free tiers) before shipping to real users.
                TileLayer(
                  urlTemplate: 'https://api.maptiler.com/maps/base-v4/{z}/{x}/{y}.png?key=WWipVbJeua9IIY8gsxvx',
                  userAgentPackageName: 'com.wasla.aio_customer_app',
                ),
                MarkerLayer(
                  markers: [
                    // The driver's own position — GoogleMap's
                    // myLocationEnabled drew this natively; flutter_map
                    // has no built-in equivalent, so it's just a marker
                    // like any other, using the position we already fetch.
                    Marker(
                      point: ll.LatLng(position.lat, position.lng),
                      width: 22,
                      height: 22,
                      child: Container(
                        decoration: BoxDecoration(
                          color: AppColors.primaryBlue,
                          shape: BoxShape.circle,
                          border: Border.all(color: Colors.white, width: 3),
                          boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.3), blurRadius: 4)],
                        ),
                      ),
                    ),
                    ...offersAsync.maybeWhen(
                      data: (orders) => _buildMarkers(context, orders),
                      orElse: () => <Marker>[],
                    ),
                  ],
                ),
              ],
            )
          else
            Container(
              color: AppColors.background,
              child: Center(
                child: _requestingLocation
                    ? const CircularProgressIndicator(color: AppColors.primaryBlue)
                    : TextButton.icon(
                        onPressed: _requestLocation,
                        icon: const Icon(Icons.my_location_rounded),
                        label: const Text('إعادة محاولة تحديد الموقع'),
                      ),
              ),
            ),

          // --- Top header: online toggle ------------------------------------
          SafeArea(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: FadeSlideIn(
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(20),
                    boxShadow: [
                      BoxShadow(color: Colors.black.withValues(alpha: 0.1), blurRadius: 16, offset: const Offset(0, 4)),
                    ],
                  ),
                  child: Row(
                    children: [
                      Container(
                        width: 10, height: 10,
                        decoration: BoxDecoration(
                          color: isOnline ? AppColors.success : AppColors.textMuted,
                          shape: BoxShape.circle,
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          isOnline ? 'متصل — في انتظار عروض التوصيل' : 'غير متصل',
                          style: const TextStyle(fontWeight: FontWeight.w700, color: AppColors.textPrimary),
                        ),
                      ),
                      Switch(
                        value: isOnline,
                        activeThumbColor: AppColors.primaryBlue,
                        onChanged: _toggleOnline,
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),

          // --- Bottom: current delivery offer(s) ------------------------------------
          Align(
            alignment: Alignment.bottomCenter,
            child: Container(
              width: double.infinity,
              constraints: BoxConstraints(maxHeight: MediaQuery.of(context).size.height * 0.42),
              decoration: const BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.vertical(top: Radius.circular(28)),
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const SizedBox(height: 10),
                  Container(width: 40, height: 4, decoration: BoxDecoration(color: AppColors.divider, borderRadius: BorderRadius.circular(2))),
                  const SizedBox(height: 12),
                  const Padding(
                    padding: EdgeInsets.symmetric(horizontal: 20),
                    child: Row(
                      children: [
                        // No manual refresh button — offers poll automatically
                        // (see driverOffersProvider) since they're time-limited;
                        // a stale "refresh to see more" habit would just show
                        // the driver expired offers he can no longer accept.
                        Text('عرض التوصيل الحالي', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
                      ],
                    ),
                  ),
                  Flexible(
                    child: offersAsync.when(
                      data: (orders) {
                        final offers = groupOffersByDeliveryGroup(orders);
                        if (offers.isEmpty) {
                          return const Padding(
                            padding: EdgeInsets.all(24),
                            child: Text('لا يوجد عرض توصيل حاليًا — سيصلك تنبيه عند توفر واحد', style: TextStyle(color: AppColors.textMuted)),
                          );
                        }
                        return ListView.builder(
                          shrinkWrap: true,
                          padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
                          itemCount: offers.length,
                          itemBuilder: (context, index) => _OfferCard(offer: offers[index]),
                        );
                      },
                      loading: () => const Padding(
                        padding: EdgeInsets.all(24),
                        child: Center(child: CircularProgressIndicator(color: AppColors.primaryBlue)),
                      ),
                      error: (e, st) => Padding(
                        padding: const EdgeInsets.all(24),
                        child: Text('تعذر تحميل عروض التوصيل: ${friendlyErrorMessage(e)}', style: const TextStyle(color: AppColors.error)),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  List<Marker> _buildMarkers(BuildContext context, List<DriverOrderModel> orders) {
    return orders
        .where((o) => o.shopLat != null && o.shopLng != null)
        .map((o) => Marker(
              point: ll.LatLng(o.shopLat!, o.shopLng!),
              width: 40,
              height: 40,
              child: GestureDetector(
                onTap: () => context.push('/driver/order/${o.id}'),
                // flutter_map has no InfoWindow equivalent — GoogleMap's
                // tap-to-reveal title/price bubble is dropped here in favor
                // of just the marker icon; tapping still navigates to the
                // order exactly like before.
                child: const Icon(Icons.storefront_rounded, color: AppColors.primaryBlue, size: 36),
              ),
            ))
        .toList();
  }
}

class _OfferCard extends ConsumerStatefulWidget {
  final DeliveryOffer offer;
  const _OfferCard({required this.offer});

  @override
  ConsumerState<_OfferCard> createState() => _OfferCardState();
}

class _OfferCardState extends ConsumerState<_OfferCard> {
  bool _loading = false;

  Future<void> _accept() async {
    setState(() => _loading = true);
    try {
      await ref.read(driverRepositoryProvider).acceptGroup(widget.offer.deliveryGroupId);
      ref.invalidate(driverOffersProvider);
      ref.invalidate(driverActiveOrdersProvider);
      if (mounted) context.push('/driver/order/${widget.offer.orders.first.id}');
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('تعذر قبول العرض: ${friendlyErrorMessage(e)}')),
      );
      setState(() => _loading = false);
    }
  }

  Future<void> _decline() async {
    setState(() => _loading = true);
    try {
      await ref.read(driverRepositoryProvider).declineGroup(widget.offer.deliveryGroupId);
      ref.invalidate(driverOffersProvider);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('تعذر رفض العرض: ${friendlyErrorMessage(e)}')),
      );
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final offer = widget.offer;
    // Multiple shops in one offer means the driver picks up from all of
    // them, in this one zone, for the same customer — see the shop chip row.
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.background,
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Container(
                width: 44, height: 44,
                decoration: BoxDecoration(gradient: AppGradients.primary, borderRadius: BorderRadius.circular(14)),
                child: Icon(
                  offer.orders.length > 1 ? Icons.storefront_outlined : Icons.storefront_rounded,
                  color: Colors.white,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      offer.orders.length > 1
                          ? '${offer.orders.length} متاجر في نفس المنطقة'
                          : offer.shopNames.first,
                      style: const TextStyle(fontWeight: FontWeight.w700),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      offer.shopNames.join(' • '),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontSize: 12, color: AppColors.textMuted),
                    ),
                  ],
                ),
              ),
              Text('${offer.total.toStringAsFixed(0)} ج.م', style: const TextStyle(fontWeight: FontWeight.w700, color: AppColors.primaryBlue)),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: OutlinedButton(
                  onPressed: _loading ? null : _decline,
                  child: const Text('رفض'),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: ElevatedButton(
                  onPressed: _loading ? null : _accept,
                  child: _loading
                      ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                      : const Text('قبول'),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}