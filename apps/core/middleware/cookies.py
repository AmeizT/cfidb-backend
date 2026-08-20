class PrintCookiesMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        print(request.COOKIES)  # will print every request's cookies
        response = self.get_response(request)
        return response