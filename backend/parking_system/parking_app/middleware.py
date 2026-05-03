from django.utils.deprecation import MiddlewareMixin

class DisableCSRFForAPIMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # Disable CSRF for any URL starting with /api/ or /map/ (if needed)
        if request.path.startswith('/api/') or request.path.startswith('/map/'):
            setattr(request, '_dont_enforce_csrf_checks', True)