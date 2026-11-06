import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart' as ll;
import '../../../core/theme/app_theme.dart';
import '../../../core/utils/error_helpers.dart';
import '../../../data/models/driver_order_model.dart';
import '../../../data/repositories/driver_repository.dart';
import '../../../data/services/location_service.dart';
import '../../../providers/driver_provider.dart';



class DriverOrderDetailScreen extends ConsumerStatefulWidget {
  final String orderId;
  const DriverOrderDetailScreen({super.key, required this.orderId});

  @override
  ConsumerState<DriverOrderDetailScreen> createState() => _DriverOrderDetailScreenState();
}

class _DriverOrderDetailScreenState extends ConsumerState<DriverOrderDetailScreen> {
  bool _actionLoading = false;
  StreamSubscription? _positionSub;
  // flutter_map has no myLocationEnabled equivalent — this replicates it by
  // reusing the same LocationService this screen already depends on: one
  // immediate fetch on open (covers a 'pending' order, before delivery
  // sharing has started), then kept fresh by _startLocationSharing's
  // stream once accepted.
  ll.LatLng? _myPosition;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _fetchOwnPositionOnce());
  }

  Future<void> _fetchOwnPositionOnce() async {
    final result = await ref.read(locationServiceProvider).getCurrentLocation();
    if (mounted && result.isSuccess) {
      setState(() => _myPosition = ll.LatLng(result.lat!, result.lng!));
    }
  }

  @override
  void dispose() {
    _positionSub?.cancel();
    super.dispose();
  }

  /// Starts pushing this driver's live position to the backend every time
  /// it changes meaningfully (see LocationService's distanceFilter) — the
  /// backend then broadcasts it to the customer via the tracking WebSocket.
  /// Stops automatically when this screen is disposed (order delivered/
  /// cancelled/navigated away) or when the subscription is cancelled below.
  void _startLocationSharing() {
    if (_positionSub != null) return;
    final locationService = ref.read(locationServiceProvider);
    final repo = ref.read(driverRepositoryProvider);
    _positionSub = locationService.positionStream().listen((position) {
      if (mounted) setState(() => _myPosition = ll.LatLng(position.latitude, position.longitude));
      repo.updateLocation(
        orderId: widget.orderId,
        lat: position.latitude,
        lng: position.longitude,
        bearing: position.heading,
        speedKmh: position.speed * 3.6,
      ).catchError((_) {
        // Best-effort — a single failed location ping shouldn't interrupt
        // the stream or surface an error to the driver mid-delivery.
      });
    });
  }

  void _stopLocationSharing() {
    _positionSub?.cancel();
    _positionSub = null;
  }

  Future<void> _acceptOffer(String deliveryGroupId) async {
    setState(() => _actionLoading = true);
    try {
      await ref.read(driverRepositoryProvider).acceptGroup(deliveryGroupId);
      ref.invalidate(driverOrderDetailProvider(widget.orderId));
      ref.invalidate(driverActiveOrdersProvider);
      ref.invalidate(driverOffersProvider);
      _startLocationSharing();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('تعذر قبول العرض: ${_readableError(e)}')),
      );
    } finally {
      if (mounted) setState(() => _actionLoading = false);
    }
  }

  Future<void> _declineOffer(String deliveryGroupId) async {
    setState(() => _actionLoading = true);
    try {
      await ref.read(driverRepositoryProvider).declineGroup(deliveryGroupId);
      ref.invalidate(driverOffersProvider);
      if (mounted) context.pop();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('تعذر رفض العرض: ${_readableError(e)}')),
      );
    } finally {
      if (mounted) setState(() => _actionLoading = false);
    }
  }

  Future<void> _updateStatus(String status) async {
    setState(() => _actionLoading = true);
    try {
      await ref.read(driverRepositoryProvider).updateOrderStatus(widget.orderId, status);
      ref.invalidate(driverOrderDetailProvider(widget.orderId));
      ref.invalidate(driverActiveOrdersProvider);
      if (status == 'delivered' || status == 'cancelled') {
        _stopLocationSharing();
        if (mounted) context.pop();
      }
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('تعذر تحديث حالة الطلب: ${_readableError(e)}')),
      );
    } finally {
      if (mounted) setState(() => _actionLoading = false);
    }
  }

  Future<void> _advanceStage(DeliveryStage nextStage) async {
    setState(() => _actionLoading = true);
    try {
      await ref.read(driverRepositoryProvider).updateDeliveryStage(widget.orderId, nextStage);
      ref.invalidate(driverOrderDetailProvider(widget.orderId));
      ref.invalidate(driverActiveOrdersProvider);
      if (nextStage == DeliveryStage.delivered || nextStage == DeliveryStage.cancelled) {
        _stopLocationSharing();
        if (mounted) context.pop();
      }
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('تعذر تحديث حالة التوصيل: ${_readableError(e)}')),
      );
    } finally {
      if (mounted) setState(() => _actionLoading = false);
    }
  }

  Future<void> _reportFailure(String reason, String? notes) async {
    setState(() => _actionLoading = true);
    try {
      await ref.read(driverRepositoryProvider).reportDeliveryFailure(widget.orderId, reason: reason, notes: notes);
      ref.invalidate(driverOrderDetailProvider(widget.orderId));
      ref.invalidate(driverActiveOrdersProvider);
      _stopLocationSharing();
      if (mounted) context.pop();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('تعذر تسجيل المشكلة: ${_readableError(e)}')),
      );
    } finally {
      if (mounted) setState(() => _actionLoading = false);
    }
  }

  Future<void> _showFailureDialog() async {
    // (reason value, Arabic label) pairs mirroring DeliveryFailureReason on
    // the backend (spec 2.10).
    const reasons = [
      ('customer_unavailable', 'العميل غير متاح'),
      ('wrong_address', 'عنوان غير صحيح'),
      ('customer_refused', 'رفض العميل استلام الطلب'),
      ('driver_issue', 'مشكلة لدى السائق'),
      ('other', 'سبب آخر'),
    ];
    final selected = await showModalBottomSheet<String>(
      context: context,
      builder: (ctx) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Padding(
              padding: EdgeInsets.all(16),
              child: Text('سبب فشل التوصيل', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 16)),
            ),
            ...reasons.map((r) => ListTile(
                  title: Text(r.$2),
                  onTap: () => Navigator.of(ctx).pop(r.$1),
                )),
          ],
        ),
      ),
    );
    if (selected != null) await _reportFailure(selected, null);
  }

  String _readableError(Object e) => friendlyErrorMessage(e);

  @override
  Widget build(BuildContext context) {
    final orderAsync = ref.watch(driverOrderDetailProvider(widget.orderId));

    return Scaffold(
      appBar: AppBar(title: const Text('تفاصيل الطلب')),
      body: orderAsync.when(
        data: (order) {
          // An accepted-but-not-yet-terminal order should be sharing
          // location — covers the case where this screen was reopened
          // after the app restarted mid-delivery. Granular stage (when
          // present) is the authoritative signal; falls back to the
          // coarse status check for older orders with no stage tracking.
          final stage = order.deliveryStage;
          final isActivelyDelivering = stage != null
              ? (stage != DeliveryStage.orderCreated &&
                  stage != DeliveryStage.branchValidated &&
                  stage != DeliveryStage.inventoryValidated &&
                  stage != DeliveryStage.deliveryValidated &&
                  stage != DeliveryStage.fulfillmentSelected &&
                  stage != DeliveryStage.providerSelected &&
                  stage != DeliveryStage.delivered &&
                  stage != DeliveryStage.cancelled &&
                  stage != DeliveryStage.failedDelivery)
              : (order.isHeadingToShop || order.isHeadingToCustomer);
          if (isActivelyDelivering) _startLocationSharing();
          return _buildContent(order);
        },
        loading: () => const Center(child: CircularProgressIndicator(color: AppColors.primaryBlue)),
        error: (e, st) => Center(child: Text('تعذر تحميل الطلب: ${friendlyErrorMessage(e)}')),
      ),
    );
  }

  Widget _buildContent(DriverOrderModel order) {
    // Before pickup, head to the exact branch fulfilling this order (spec
    // 2.4) — falls back to the shop's own location for shops with no
    // branches, via pickupLat/pickupLng's getter. After pickup, head to
    // the customer, same as before this feature existed.
    final headingToCustomer = order.deliveryStage != null
        ? (order.deliveryStage == DeliveryStage.pickedUp ||
            order.deliveryStage == DeliveryStage.inTransit ||
            order.deliveryStage == DeliveryStage.arrivedAtCustomer)
        : order.isHeadingToCustomer;

    final destination = headingToCustomer
        ? (order.deliveryLat != null && order.deliveryLng != null
            ? ll.LatLng(order.deliveryLat!, order.deliveryLng!)
            : null)
        : (order.pickupLat != null && order.pickupLng != null
            ? ll.LatLng(order.pickupLat!, order.pickupLng!)
            : null);

    return Column(
      children: [
        Expanded(
          flex: 3,
          child: destination == null
              ? Container(
                  color: AppColors.background,
                  child: const Center(child: Text('لا يوجد موقع متاح لعرضه على الخريطة')),
                )
              : FlutterMap(
                  options: MapOptions(initialCenter: destination, initialZoom: 14),
                  children: [
                    TileLayer(
                      urlTemplate: 'https://api.maptiler.com/maps/base-v4/{z}/{x}/{y}.png?key=WWipVbJeua9IIY8gsxvx',
                      userAgentPackageName: 'com.wasla.aio_customer_app',
                    ),
                    MarkerLayer(
                      markers: [
                        Marker(
                          point: destination,
                          width: 40,
                          height: 40,
                          child: Icon(
                            headingToCustomer ? Icons.home_rounded : Icons.storefront_rounded,
                            color: AppColors.error,
                            size: 36,
                          ),
                        ),
                        // Replicates myLocationEnabled — see _myPosition's docstring above.
                        if (_myPosition != null)
                          Marker(
                            point: _myPosition!,
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
                      ],
                    ),
                  ],
                ),
        ),
        Expanded(
          flex: 2,
          child: Container(
            width: double.infinity,
            padding: const EdgeInsets.all(20),
            decoration: const BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.vertical(top: Radius.circular(28)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Row(
                  children: [
                    Container(
                      width: 44, height: 44,
                      decoration: BoxDecoration(gradient: AppGradients.primary, borderRadius: BorderRadius.circular(14)),
                      child: const Icon(Icons.storefront_rounded, color: Colors.white),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(order.pickupName, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16)),
                          Text('${order.total.toStringAsFixed(0)} ج.م', style: const TextStyle(color: AppColors.primaryBlue, fontWeight: FontWeight.w700)),
                        ],
                      ),
                    ),
                    if (order.status != 'pending' && order.customerName != null) ...[
                      IconButton(
                        icon: const Icon(Icons.chat_bubble_outline_rounded, color: AppColors.primaryBlue),
                        onPressed: () => context.push('/chat/${order.id}?name=${Uri.encodeComponent(order.customerName!)}'),
                      ),
                      IconButton(
                        icon: const Icon(Icons.call_outlined, color: AppColors.primaryBlue),
                        onPressed: () => context.push('/call/${order.id}?name=${Uri.encodeComponent(order.customerName!)}'),
                      ),
                    ],
                  ],
                ),
                const SizedBox(height: 12),
                if (order.deliveryAddress != null)
                  Text('عنوان التوصيل: ${order.deliveryAddress}', style: const TextStyle(color: AppColors.textSecondary, fontSize: 13)),
                if (order.deliveryStage != null) ...[
                  const SizedBox(height: 6),
                  Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                        decoration: BoxDecoration(
                          color: AppColors.primaryBlue.withValues(alpha: 0.08),
                          borderRadius: BorderRadius.circular(20),
                        ),
                        child: Text(
                          order.deliveryStage!.arabicLabel,
                          style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w600, color: AppColors.primaryBlue),
                        ),
                      ),
                      if ((order.liveEtaMinutes ?? order.etaMinutes) != null) ...[
                        const SizedBox(width: 8),
                        Icon(Icons.access_time_rounded, size: 14, color: AppColors.textMuted),
                        const SizedBox(width: 3),
                        Text('${order.liveEtaMinutes ?? order.etaMinutes} دقيقة',
                            style: const TextStyle(fontSize: 11.5, color: AppColors.textMuted)),
                      ],
                    ],
                  ),
                ],
                const Spacer(),
                _buildActionButton(order),
                if (order.deliveryStage != null &&
                    order.deliveryStage != DeliveryStage.delivered &&
                    order.deliveryStage != DeliveryStage.cancelled &&
                    order.deliveryStage != DeliveryStage.failedDelivery &&
                    order.status != 'pending') ...[
                  const SizedBox(height: 8),
                  TextButton.icon(
                    onPressed: _actionLoading ? null : _showFailureDialog,
                    icon: const Icon(Icons.report_problem_outlined, size: 18, color: AppColors.error),
                    label: const Text('الإبلاغ عن مشكلة في التوصيل', style: TextStyle(color: AppColors.error)),
                  ),
                ],
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildActionButton(DriverOrderModel order) {
    if (order.status == 'pending') {
      final groupId = order.deliveryGroupId ?? order.id;
      return Row(
        children: [
          Expanded(
            child: SizedBox(
              height: 56,
              child: OutlinedButton(
                onPressed: _actionLoading ? null : () => _declineOffer(groupId),
                child: const Text('رفض'),
              ),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            flex: 2,
            child: SizedBox(
              height: 56,
              child: ElevatedButton(
                onPressed: _actionLoading ? null : () => _acceptOffer(groupId),
                child: _actionLoading
                    ? const SizedBox(width: 24, height: 24, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                    : const Text('قبول — التوجه إلى المتجر'),
              ),
            ),
          ),
        ],
      );
    }

    // Granular stage flow (spec 1.8/2.4-2.9) — one "advance" button that
    // always shows the SINGLE next step, since a driver mid-delivery
    // should never be choosing between several possible next stages.
    final stage = order.deliveryStage;
    if (stage != null) {
      final buttonSpec = _stageButtonSpec(stage);
      if (buttonSpec == null) return const SizedBox.shrink(); // terminal stage, nothing to do
      return SizedBox(
        height: 56,
        child: ElevatedButton(
          onPressed: _actionLoading ? null : () => _advanceStage(buttonSpec.$2),
          style: ElevatedButton.styleFrom(backgroundColor: buttonSpec.$3),
          child: _actionLoading
              ? const SizedBox(width: 24, height: 24, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
              : Text(buttonSpec.$1),
        ),
      );
    }

    // Fallback for orders with no granular stage tracking (older orders,
    // or shops with no branch) — the original coarse two-step flow,
    // completely unchanged.
    if (order.isHeadingToShop) {
      return SizedBox(
        height: 56,
        child: ElevatedButton(
          onPressed: _actionLoading ? null : () => _updateStatus('out_for_delivery'),
          style: ElevatedButton.styleFrom(backgroundColor: AppColors.warning),
          child: _actionLoading
              ? const SizedBox(width: 24, height: 24, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
              : const Text('تم استلام الطلب — التوجه إلى العميل'),
        ),
      );
    }
    if (order.isHeadingToCustomer) {
      return SizedBox(
        height: 56,
        child: ElevatedButton(
          onPressed: _actionLoading ? null : () => _updateStatus('delivered'),
          style: ElevatedButton.styleFrom(backgroundColor: AppColors.success),
          child: _actionLoading
              ? const SizedBox(width: 24, height: 24, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
              : const Text('تم توصيل الطلب'),
        ),
      );
    }
    return const SizedBox.shrink();
  }

  /// (button label, target stage, button color) for the SINGLE next action
  /// available from [current]. Returns null once there's nothing left for
  /// the driver to do (delivered/cancelled/failed — see the failure-dialog
  /// path for how those are reached instead of this button).
  ///
  /// Some backend stages (waiting_for_order) are intentionally skipped in
  /// this UI — the backend's forward-skip rule (delivery_service.
  /// is_valid_transition) allows moving arrived_at_branch -> picked_up
  /// directly, so the driver isn't forced through a step that adds no
  /// real information for him.
  (String, DeliveryStage, Color)? _stageButtonSpec(DeliveryStage current) {
    switch (current) {
      case DeliveryStage.driverAssigned:
        return ('التوجه إلى الفرع', DeliveryStage.goingToBranch, AppColors.primaryBlue);
      case DeliveryStage.goingToBranch:
        return ('وصلت إلى الفرع', DeliveryStage.arrivedAtBranch, AppColors.primaryBlue);
      case DeliveryStage.arrivedAtBranch:
      case DeliveryStage.waitingForOrder:
        return ('استلمت الطلب من الفرع', DeliveryStage.pickedUp, AppColors.warning);
      case DeliveryStage.pickedUp:
        return ('بدء التوجه إلى العميل', DeliveryStage.inTransit, AppColors.warning);
      case DeliveryStage.inTransit:
        return ('وصلت إلى العميل', DeliveryStage.arrivedAtCustomer, AppColors.success);
      case DeliveryStage.arrivedAtCustomer:
        return ('تم تسليم الطلب', DeliveryStage.delivered, AppColors.success);
      // Pre-driver stages (shouldn't normally be seen here since accepting
      // an offer immediately sets driver_assigned) and recoverable
      // exceptions — resume forward from where the exception left off.
      case DeliveryStage.branchDelay:
      case DeliveryStage.driverRejected:
      case DeliveryStage.providerFailed:
      case DeliveryStage.customerUnavailable:
        return ('استئناف التوصيل', DeliveryStage.driverAssigned, AppColors.primaryBlue);
      case DeliveryStage.orderCreated:
      case DeliveryStage.branchValidated:
      case DeliveryStage.inventoryValidated:
      case DeliveryStage.deliveryValidated:
      case DeliveryStage.fulfillmentSelected:
      case DeliveryStage.providerSelected:
        return ('التوجه إلى الفرع', DeliveryStage.goingToBranch, AppColors.primaryBlue);
      case DeliveryStage.delivered:
      case DeliveryStage.cancelled:
      case DeliveryStage.failedDelivery:
      case DeliveryStage.inventoryUnavailable:
        return null;
    }
  }
}