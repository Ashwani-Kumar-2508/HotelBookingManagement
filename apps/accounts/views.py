from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import User


def login_view(request):
    if request.user.is_authenticated:
        return redirect('core:home')

    next_url = request.GET.get('next', 'core:home')

    if request.method == 'POST':
        # Check for 1-click demo login trigger
        demo_role = request.POST.get('demo_role')
        if demo_role:
            role_email_map = {
                'admin': 'admin@grandview.com',
                'staff': 'staff@grandview.com',
                'guest': 'guest@example.com',
                'guest2': 'sarah@example.com',
            }
            target_email = role_email_map.get(demo_role)
            if target_email:
                try:
                    user = User.objects.get(email=target_email)
                    login(request, user)
                    messages.success(request, f"Signed in as {user.get_role_display()}: {user.get_full_name() or user.email}")
                    if user.is_hotel_admin:
                        return redirect('reports:dashboard')
                    elif user.is_hotel_staff:
                        return redirect('bookings:staff_desk')
                    return redirect(next_url or 'core:home')
                except User.DoesNotExist:
                    messages.error(request, f"Demo user {target_email} not found. Please run seed script.")
                    return redirect('accounts:login')

        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')

        if not email or not password:
            messages.error(request, "Please enter both email and password.")
            return render(request, 'accounts/login.html', {'next': next_url})

        user = authenticate(request, username=email, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, f"Welcome back, {user.get_full_name() or user.email}!")
            if user.is_hotel_admin:
                return redirect(next_url if next_url != 'core:home' else 'reports:dashboard')
            elif user.is_hotel_staff:
                return redirect(next_url if next_url != 'core:home' else 'bookings:staff_desk')
            return redirect(next_url)
        else:
            messages.error(request, "Invalid email address or password.")

    return render(request, 'accounts/login.html', {'next': next_url})


def register_view(request):
    if request.user.is_authenticated:
        return redirect('core:home')

    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()

        if not email or not password or not first_name or not last_name:
            messages.error(request, "Please fill in all required fields.")
            return render(request, 'accounts/register.html')

        if len(password) < 6:
            messages.error(request, "Password must be at least 6 characters.")
            return render(request, 'accounts/register.html')

        if User.objects.filter(email=email).exists():
            messages.error(request, "An account with this email already exists.")
            return render(request, 'accounts/register.html')

        username = email.split('@')[0] + str(User.objects.count() + 1)
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number,
            role=User.Role.GUEST
        )
        login(request, user)
        messages.success(request, f"Welcome to GrandView Hotel, {user.first_name}!")
        return redirect('core:home')

    return render(request, 'accounts/register.html')


def logout_view(request):
    logout(request)
    messages.info(request, "You have been signed out successfully.")
    return redirect('accounts:login')


@login_required
def profile_view(request):
    if request.method == 'POST':
        request.user.first_name = request.POST.get('first_name', request.user.first_name).strip()
        request.user.last_name = request.POST.get('last_name', request.user.last_name).strip()
        request.user.phone_number = request.POST.get('phone_number', request.user.phone_number).strip()
        request.user.save()
        messages.success(request, "Profile updated successfully.")
        return redirect('accounts:profile')
    return render(request, 'accounts/profile.html')
