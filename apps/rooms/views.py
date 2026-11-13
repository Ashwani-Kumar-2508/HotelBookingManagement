from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from apps.accounts.decorators import hotel_admin_required, hotel_staff_required
from .models import RoomType, Room, Amenity
from decimal import Decimal


@hotel_admin_required
def room_type_list(request):
    """Admin view: List all room types and their configurations."""
    room_types = RoomType.objects.prefetch_related('amenities', 'rooms').all()
    return render(request, 'rooms/room_type_list.html', {'room_types': room_types})


@hotel_admin_required
def room_type_create(request):
    """Admin view: Create a new room type with amenities and pricing."""
    amenities = Amenity.objects.all()

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        tagline = request.POST.get('tagline', '').strip()
        description = request.POST.get('description', '').strip()
        base_price = request.POST.get('base_price', '0')
        weekend_price = request.POST.get('weekend_price', '')
        max_guests = request.POST.get('max_guests', '2')
        bed_type = request.POST.get('bed_type', '1 King Bed').strip()
        size_sqft = request.POST.get('size_sqft', '450')
        image_url = request.POST.get('image_url', '').strip()
        selected_amenity_ids = request.POST.getlist('amenities')

        if not name or not base_price:
            messages.error(request, "Room type name and base price are required.")
            return render(request, 'rooms/room_type_form.html', {'amenities': amenities})

        try:
            rt = RoomType.objects.create(
                name=name,
                tagline=tagline,
                description=description,
                base_price=Decimal(base_price),
                weekend_price=Decimal(weekend_price) if weekend_price else None,
                max_guests=int(max_guests),
                bed_type=bed_type,
                size_sqft=int(size_sqft),
                image_url=image_url or 'https://images.unsplash.com/photo-1590490360182-c33d57733427?auto=format&fit=crop&w=800&q=80'
            )
            if selected_amenity_ids:
                rt.amenities.set(selected_amenity_ids)
            messages.success(request, f"Room type '{rt.name}' created successfully.")
            return redirect('rooms:room_type_list')
        except Exception as e:
            messages.error(request, f"Error creating room type: {str(e)}")

    return render(request, 'rooms/room_type_form.html', {'amenities': amenities, 'is_edit': False})


@hotel_admin_required
def room_type_edit(request, pk):
    """Admin view: Edit an existing room type, its rates, and amenities."""
    rt = get_object_or_404(RoomType, pk=pk)
    amenities = Amenity.objects.all()

    if request.method == 'POST':
        rt.name = request.POST.get('name', rt.name).strip()
        rt.tagline = request.POST.get('tagline', rt.tagline).strip()
        rt.description = request.POST.get('description', rt.description).strip()
        rt.base_price = Decimal(request.POST.get('base_price', rt.base_price))
        weekend_price = request.POST.get('weekend_price', '')
        rt.weekend_price = Decimal(weekend_price) if weekend_price else None
        rt.max_guests = int(request.POST.get('max_guests', rt.max_guests))
        rt.bed_type = request.POST.get('bed_type', rt.bed_type).strip()
        rt.size_sqft = int(request.POST.get('size_sqft', rt.size_sqft))
        rt.image_url = request.POST.get('image_url', rt.image_url).strip()
        rt.is_active = request.POST.get('is_active') == 'on'

        selected_amenity_ids = request.POST.getlist('amenities')
        rt.amenities.set(selected_amenity_ids)
        rt.save()

        messages.success(request, f"Room type '{rt.name}' updated successfully.")
        return redirect('rooms:room_type_list')

    return render(request, 'rooms/room_type_form.html', {
        'room_type': rt,
        'amenities': amenities,
        'is_edit': True,
        'current_amenity_ids': list(rt.amenities.values_list('id', flat=True))
    })


@hotel_staff_required
def room_inventory_list(request):
    """Staff/Admin view: View all physical rooms, filter by floor/status, and manage."""
    rooms = Room.objects.select_related('room_type').all()
    floor_filter = request.GET.get('floor')
    status_filter = request.GET.get('status')

    if floor_filter:
        rooms = rooms.filter(floor=floor_filter)
    if status_filter:
        rooms = rooms.filter(status=status_filter)

    floors = sorted(list(set(Room.objects.values_list('floor', flat=True))))
    return render(request, 'rooms/room_inventory_list.html', {
        'rooms': rooms,
        'floors': floors,
        'statuses': Room.Status.choices,
        'selected_floor': floor_filter,
        'selected_status': status_filter,
    })


@hotel_admin_required
def room_create(request):
    """Admin view: Add an individual physical room."""
    room_types = RoomType.objects.filter(is_active=True)

    if request.method == 'POST':
        room_number = request.POST.get('room_number', '').strip().upper()
        room_type_id = request.POST.get('room_type')
        floor = request.POST.get('floor', '1')
        status = request.POST.get('status', Room.Status.AVAILABLE)
        housekeeping_notes = request.POST.get('housekeeping_notes', '').strip()

        if not room_number or not room_type_id:
            messages.error(request, "Room number and room type are required.")
            return render(request, 'rooms/room_form.html', {'room_types': room_types, 'statuses': Room.Status.choices})

        if Room.objects.filter(room_number=room_number).exists():
            messages.error(request, f"Room {room_number} already exists.")
            return render(request, 'rooms/room_form.html', {'room_types': room_types, 'statuses': Room.Status.choices})

        room_type = get_object_or_404(RoomType, pk=room_type_id)
        room = Room.objects.create(
            room_number=room_number,
            room_type=room_type,
            floor=int(floor),
            status=status,
            housekeeping_notes=housekeeping_notes
        )
        messages.success(request, f"Room {room.room_number} added to inventory.")
        return redirect('rooms:room_inventory')

    return render(request, 'rooms/room_form.html', {'room_types': room_types, 'statuses': Room.Status.choices, 'is_edit': False})


@hotel_staff_required
def update_room_status(request, pk):
    """HTMX / Staff action: Instantly update room status (e.g. Mark Clean, Mark Maintenance)."""
    room = get_object_or_404(Room, pk=pk)
    if request.method == 'POST':
        new_status = request.POST.get('status')
        notes = request.POST.get('notes')

        if new_status in dict(Room.Status.choices):
            old_status = room.status
            room.status = new_status
            if notes is not None:
                room.housekeeping_notes = notes
            room.save()

            # Log audit trail
            from apps.bookings.models import BookingAuditLog
            BookingAuditLog.objects.create(
                room=room,
                user=request.user,
                action=BookingAuditLog.Action.ROOM_STATUS_CHANGED,
                title=f"Room {room.room_number} status changed to {room.get_status_display()}",
                details=f"Status transitioned from {old_status} to {new_status} by {request.user.email}."
            )

            if request.headers.get('HX-Request'):
                return render(request, 'rooms/partials/room_status_pill.html', {'room': room})
            
            messages.success(request, f"Room {room.room_number} status updated to {room.get_status_display()}.")

    return redirect('rooms:room_inventory')
