from io import BytesIO
from django.http import HttpResponse
from django.template.loader import get_template
from .models import *
from django.core.files.base import ContentFile
from django.core.files import File

from xhtml2pdf import pisa


def new_render_to_file_pools(template_src, filename, user_pool_id, context_dict={}):
    template = get_template(template_src)
    html  = template.render(context_dict)
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)
    user_pool = UserPoolSlots.objects.get(pk=user_pool_id)
    print(user_pool.slots_value)
    if not pdf.err:
        with open(filename, 'wb+') as output:
            pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), output)
            user_pool.contract_file.save(filename, output)
        return HttpResponse(result.getvalue(), content_type='application/pdf')
    return None 

