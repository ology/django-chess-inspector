from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import redirect, render, reverse
import json

from .controller import Controller

ctrl = Controller()

def login_page(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')
        if not User.objects.filter(username=username).exists():
            messages.error(request, "Invalid login")
            return redirect('/accounts/login/')
        user = authenticate(username=username, password=password)
        if user is None:
            messages.error(request, "Invalid login")
            return redirect('/accounts/login/')
        login(request, user)
        request.session['user_id'] = user.id
        request.session.save()
        return redirect("game:index")
    return render(request, 'login.html')

@login_required
def index(request):
    ctrl.current_user_id = request.session.get('user_id')
    is_cover = False
    if request.method == "POST":
        ctrl.fen = request.POST.get('fen')
        ctrl.en_passant = request.POST.get('en_passant')
        is_cover = request.POST.get('is_cover')
    else:
        ctrl.fen = request.GET.get('fen')
        ctrl.en_passant = request.GET.get('en_passant')
        is_cover = request.GET.get('is_cover')
    coverage = ctrl.get_coverage()
    coverage = json.dumps(coverage)
    context = { "fen": ctrl.board.fen(), "coverage": coverage, "is_cover": is_cover }
    return render(request, "game/index.html", context)

@login_required
def pgn(request):
    ctrl.current_user_id = request.session.get('user_id')
    if request.method == "POST" and request.FILES['pgn']:
        is_cover = request.POST.get('is_cover')
        en_passant = request.POST.get('en_passant')
        pgn = request.FILES['pgn']
        fen = ctrl.pgn(pgn)
        return redirect(reverse("game:index") + f"?fen={fen}&is_cover={is_cover}&en_passant={en_passant}")
    return redirect('game:index')
