from rest_framework.pagination import PageNumberPagination


class MyDefaultSetPagination(PageNumberPagination):

    page_size = 100 

    def get_paginated_response(self, data):
        response = super(MyDefaultSetPagination, self).get_paginated_response(data)
        response.data['total_pages'] = self.page.paginator.num_pages
        response.data['page'] = self.page.number
        return response