from io import BytesIO
from django.http import HttpResponse
from django.template.loader import get_template
from .models import UserInvestment, UserInvestmentTopups
from django.core.files.base import ContentFile
from django.core.files import File

from xhtml2pdf import pisa



def new_render_to_file(template_src, filename, txn_code, context_dict={}):
    template = get_template(template_src)
    html  = template.render(context_dict)
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)
    investment = UserInvestment.objects.get(txn_code=txn_code)
    print(investment.amount)
    if not pdf.err:
        with open(filename, 'wb+') as output:
            pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), output)
            investment.contract_file.save(filename, output)
        return HttpResponse(result.getvalue(), content_type='application/pdf')
    return None 





def new_render_to_file_top_up(template_src, filename, top_up_id, context_dict={}):
    template = get_template(template_src)
    html  = template.render(context_dict)
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)
    top_up = UserInvestmentTopups.objects.get(pk=top_up_id)
    print(top_up.amount)
    if not pdf.err:
        with open(filename, 'wb+') as output:
            pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), output)
            top_up.contract_file.save(filename, output)
        return HttpResponse(result.getvalue(), content_type='application/pdf')
    return None 

