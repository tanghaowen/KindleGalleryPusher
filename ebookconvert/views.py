from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render
from django.http import Http404
from mainsite.models import EbookConvertQueue, EbookConvertOver


# Create your views here.

@login_required
def convert_queue(request):
    if request.method == 'GET' and request.user.username == 'admin':
        user = request.user
        page_idx = request.GET.get("page", 1)
        show_over_task = request.GET.get("over", '0') == '1'

        if show_over_task:
            tasks = EbookConvertOver.objects.all().order_by('over_date')
        else:
            tasks = EbookConvertQueue.objects.all().order_by('added_date')
        pages = Paginator(tasks, 20)
        page = pages.page(page_idx)
        context = {"page": page,
                   "user": user,
                   "show_over_task": show_over_task}
        return render(request, 'ebookconvert/convert_queue.html', context=context)

    raise Http404
