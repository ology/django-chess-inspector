from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import redirect, render, reverse
import json
import logging
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
    if request.method == "POST":
        ctrl.logger.error(f"P: {request.POST}")
        ctrl.fen = request.POST.get('fen')
    coverage = ctrl.get_coverage()
    coverage = json.dumps(coverage)
    context = { "fen": ctrl.board.fen(), "coverage": coverage }
    return render(request, "game/index.html", context)
