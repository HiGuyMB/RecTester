import json
import re
import datetime
from pprint import pprint

import hashlib
from django.contrib.auth.models import User, Group
from django.core.files.uploadedfile import UploadedFile
from django.db import connection
from django.db.models import Count, Q
from django.http import HttpResponse, Http404, FileResponse, HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.utils.http import urlencode
from django.views import generic
from rest_framework import viewsets, permissions

# Create your views here.
from rest_framework import generics
from rest_framework.decorators import action, renderer_classes, api_view
from rest_framework.exceptions import NotFound
from rest_framework.pagination import CursorPagination, LimitOffsetPagination
from rest_framework.renderers import TemplateHTMLRenderer, JSONRenderer
from rest_framework.response import Response

from RecTester import settings
from recapp.models import Score, Submission, Run, guess_time
from recapp.permissions import SubmissionPermissions
from recapp.serializers import SubmissionSerializer, UserSerializer, GroupSerializer, ScoreSerializer, RunSerializer


def difference_count(os_one, os_two, include_error=True):
    if include_error:
        query = f'''SELECT COUNT(*)
        FROM (SELECT *
              FROM recapp_score score1
                       JOIN
                   recapp_run run1
                   ON score1.id = run1.score_id
              WHERE run1.os == %s) run1
                 JOIN
             (SELECT *
              FROM recapp_score score2
                       JOIN
                   recapp_run run2
                   ON score2.id = run2.score_id
              WHERE run2.os == %s) run2
             ON run1.submission_id == run2.submission_id
                 JOIN recapp_submission sub ON run1.submission_id == sub.id
        WHERE run1.error != run2.error
           OR run1.success != run2.success
           OR run1.score_time != run2.score_time
           OR run1.elapsed_time != run2.elapsed_time
           OR run1.bonus_time != run2.bonus_time
       '''
    else:
        query = f'''SELECT COUNT(*)
            FROM (SELECT *
                  FROM recapp_score score1
                           JOIN
                       recapp_run run1
                       ON score1.id = run1.score_id
                  WHERE run1.os == %s) run1
                     JOIN
                 (SELECT *
                  FROM recapp_score score2
                           JOIN
                       recapp_run run2
                       ON score2.id = run2.score_id
                  WHERE run2.os == %s) run2
                 ON run1.submission_id == run2.submission_id
                     JOIN recapp_submission sub ON run1.submission_id == sub.id
            WHERE run1.error IS NULL
              AND run2.error IS NULL
              AND run1.success
              AND run2.success
              AND (
                        run1.score_time != run2.score_time
                    OR run1.elapsed_time != run2.elapsed_time
                    OR run1.bonus_time != run2.bonus_time
                )
            '''
    with connection.cursor() as cursor:
        cursor.execute(query, [os_one, os_two])
        return cursor.fetchone()[0]


def find_differences(os_one, os_two, include_error=True, order='DESC'):
    order = 'DESC' if order == 'DESC' else 'ASC'
    if include_error:
        query = f'''SELECT sub.*
        FROM (SELECT *
              FROM recapp_score score1
                       JOIN
                   recapp_run run1
                   ON score1.id = run1.score_id
              WHERE run1.os == %s) run1
                 JOIN
             (SELECT *
              FROM recapp_score score2
                       JOIN
                   recapp_run run2
                   ON score2.id = run2.score_id
              WHERE run2.os == %s) run2
             ON run1.submission_id == run2.submission_id
                 JOIN recapp_submission sub ON run1.submission_id == sub.id
        WHERE run1.error != run2.error
           OR run1.success != run2.success
           OR run1.score_time != run2.score_time
           OR run1.elapsed_time != run2.elapsed_time
           OR run1.bonus_time != run2.bonus_time
       ORDER BY sub.upload_date {order}
       '''
    else:
        query = f'''SELECT sub.*
            FROM (SELECT *
                  FROM recapp_score score1
                           JOIN
                       recapp_run run1
                       ON score1.id = run1.score_id
                  WHERE run1.os == %s) run1
                     JOIN
                 (SELECT *
                  FROM recapp_score score2
                           JOIN
                       recapp_run run2
                       ON score2.id = run2.score_id
                  WHERE run2.os == %s) run2
                 ON run1.submission_id == run2.submission_id
                     JOIN recapp_submission sub ON run1.submission_id == sub.id
            WHERE run1.error IS NULL
              AND run2.error IS NULL
              AND run1.success
              AND run2.success
              AND (
                        run1.score_time != run2.score_time
                    OR run1.elapsed_time != run2.elapsed_time
                    OR run1.bonus_time != run2.bonus_time
                )
            ORDER BY sub.upload_date {order}
            '''
    for s in Submission.objects.raw(query, [os_one, os_two]).iterator():
        yield [r for r in s.runs.all() if r.os == os_one][0], [r for r in s.runs.all() if r.os == os_two][0]


def first_n(n, scores):
    i = 0
    for score in scores:
        i += 1
        yield score
        if i == n:
            break


def first_n_offset(n, offset, scores):
    i = 0
    for score in scores:
        i += 1
        if i < offset:
            continue
        yield score
        if i == n + offset:
            break


def first_n_unique(n, scores):
    i = 0
    seen = set()
    for score in scores:
        if score.run.submission in seen:
            continue
        seen.add(score.run.submission)
        i += 1
        yield score
        if i == n:
            break


last_check = {}


def index(request):
    if request.method != 'GET':
        return HttpResponseBadRequest()
    latest_count = 10
    latest_submissions = first_n(latest_count, Submission.objects.order_by('-upload_date'))
    latest_runs = first_n(latest_count, Score.objects.order_by('-run__run_date'))

    fastest_scores = first_n_unique(5, Score.objects.filter(Q(run__submission__isnull=False, success=True)).order_by('score_time'))
    fastest_realtime = first_n_unique(5, Score.objects.filter(Q(run__submission__isnull=False, success=True)).order_by('elapsed_time'))
    highest_fps = first_n_unique(5, Score.objects.filter(Q(run__submission__isnull=False, success=True, run__submission__is_tas=False)).order_by('-fps'))
    slowest_scores = first_n_unique(5, Score.objects.filter(Q(run__submission__isnull=False, success=True)).order_by('-score_time'))
    slowest_realtime = first_n_unique(5, Score.objects.filter(Q(run__submission__isnull=False, success=True)).order_by('-elapsed_time'))
    lowest_fps = first_n_unique(5, Score.objects.filter(Q(run__submission__isnull=False, success=True)).order_by('fps'))

    problem_children = first_n(5, find_differences('windows-newphys221029', 'windows'))
    mac_win_diff = first_n(5, find_differences('windows', 'mac', False))

    live_runners = []
    global last_check
    for runner, check in last_check.items():
        if datetime.datetime.now() - check < datetime.timedelta(minutes=30):
            live_runners.append(runner.username)

    return render(request, 'scores/index.html', {
        'latest_submissions': latest_submissions,
        'latest_runs': latest_runs,
        'fastest_scores': fastest_scores,
        'fastest_realtime': fastest_realtime,
        'highest_fps': highest_fps,
        'slowest_scores': slowest_scores,
        'slowest_realtime': slowest_realtime,
        'lowest_fps': lowest_fps,
        'problem_children': problem_children,
        'mac_win_diff': mac_win_diff,
        'live_runners': live_runners
    })


def newest(request):
    if request.method != 'GET':
        return HttpResponseBadRequest()

    latest_submissions = Submission.objects.order_by('-upload_date')[:100]
    latest_runs = Score.objects.order_by('-run__run_date')[:100]

    return render(request, 'scores/list.html', {
        'list_name': 'newest',
        'latest_submissions': latest_submissions,
        'latest_runs': latest_runs,
    })


@api_view(['GET'])
@renderer_classes([TemplateHTMLRenderer, JSONRenderer])
def compare(request, os1, os2):
    if request.method != 'GET':
        return HttpResponseBadRequest()

    count = difference_count(os1, os2)

    offset = int(request.GET.get('offset', '0'))
    limit = 100
    pages = []
    for (i, off) in enumerate(range(0, count, limit)):
        pages.append((off, i + 1))

    differences = find_differences(os1, os2, order='ASC')
    if request.accepted_renderer.format == 'html':
        os1 = os1[0].upper() + os1[1:]
        os2 = os2[0].upper() + os2[1:]

        return Response({
            'list_name': 'compare',
            'differences': list(first_n_offset(limit, offset, differences)),
            'os1': os1,
            'os2': os2,
            'pages': pages
        }, template_name='scores/list.html')
    else:
        subs = [r[0].submission for r in list(differences)]
        serializer = SubmissionSerializer(data=subs, many=True, context={'request': request})
        serializer.is_valid()
        data = serializer.data
        return Response(data)


def discrepancies(request):
    if request.method != 'GET':
        return HttpResponseBadRequest()

    categories = [
        ('Mac vs Windows', 'mac', 'windows'),
        ('Newphys Broken (2022-02-06)', 'windows', 'windows-newphys220206'),
        ('Newphys Broken (2022-10-29)', 'windows', 'windows-newphys221029'),
    ]

    return render(request, 'scores/discrepancies.html', {
        'categories': categories,
    })


def best(request):
    if request.method != 'GET':
        return HttpResponseBadRequest()

    fastest_scores = first_n_unique(100, Score.objects.filter(Q(run__submission__isnull=False, success=True)).order_by('score_time'))
    fastest_realtime = first_n_unique(100, Score.objects.filter(Q(run__submission__isnull=False, success=True)).order_by('elapsed_time'))
    highest_fps = first_n_unique(100, Score.objects.filter(Q(run__submission__isnull=False, success=True, run__submission__is_tas=False)).order_by('-fps'))

    return render(request, 'scores/list.html', {
        'list_name': 'best',
        'fastest_scores': fastest_scores,
        'fastest_realtime': fastest_realtime,
        'highest_fps': highest_fps,
    })


def worst(request):
    if request.method != 'GET':
        return HttpResponseBadRequest()

    slowest_scores = first_n_unique(100, Score.objects.filter(Q(run__submission__isnull=False, success=True)).order_by('-score_time'))
    slowest_realtime = first_n_unique(100, Score.objects.filter(Q(run__submission__isnull=False, success=True)).order_by('-elapsed_time'))
    lowest_fps = first_n_unique(100, Score.objects.filter(Q(run__submission__isnull=False, success=True)).order_by('fps'))

    return render(request, 'scores/list.html', {
        'list_name': 'worst',
        'slowest_scores': slowest_scores,
        'slowest_realtime': slowest_realtime,
        'lowest_fps': lowest_fps,
    })


def detail(request, pk):
    if request.method != 'GET':
        return HttpResponseBadRequest()

    submission = get_object_or_404(Submission, id=pk)
    return render(request, 'scores/detail.html', {
        'submission': submission,
        'runs': list(submission.runs.all())
    })


def download(request, pk):
    if request.method != 'GET':
        return HttpResponseBadRequest()

    submission = get_object_or_404(Submission, id=pk)
    response = FileResponse(submission.file.open('rb'), content_type='application/octet-stream')
    response['Content-Length'] = submission.file.size
    response['Content-Disposition'] = f'attachment; filename="{submission.name}"'
    return response


def upload(request):
    if request.method != 'POST':
        return render(request, 'scores/upload.html', {
            'error': request.GET.get('error')
        })

    if 'rec' not in request.FILES or len(request.FILES['rec']) == 0:
        return HttpResponseRedirect(reverse('recapp:upload') + '?' + urlencode([('error', 'No File Submitted')]))
    if 'expected' not in request.POST:
        return HttpResponseRedirect(reverse('recapp:upload') + '?' + urlencode([('error', 'Bad parameters')]))

    expected_time = request.POST['expected']
    try:
        expected_time = int(expected_time)
    except ValueError:
        expected_time = None

    sub = Submission.create_or_find({
        'file': request.FILES['rec'],
        'is_tas': request.POST.get('tas', 'off') == 'on',
        'expected_time': expected_time
    })

    if expected_time is None:
        sub.expected_time = guess_time(sub)
        sub.save()

    return HttpResponseRedirect(reverse('recapp:detail', args=[sub.id]))


class SubmissionViewSet(viewsets.ModelViewSet):

    class SubmissionPagination(LimitOffsetPagination):
        ordering = '-upload_date'

        def get_limit(self, request):
            if request.user.is_authenticated:
                return 50
            else:
                return 5

    queryset = Submission.objects.all().order_by('-upload_date')
    serializer_class = SubmissionSerializer
    permission_classes = [SubmissionPermissions]
    pagination_class = SubmissionPagination

    @action(methods=['GET'], detail=True)
    def download(self, *args, **kwargs):
        instance = self.get_object()
        handle = instance.file.open()

        response = FileResponse(handle, content_type='application/octet-stream')
        response['Content-Length'] = instance.file.size
        response['Content-Disposition'] = f'attachment; filename="{instance.name}"'
        return response


class PendingSubmissionViewSet(viewsets.ReadOnlyModelViewSet):

    class PendingSubmissionPagination(CursorPagination):
        ordering = 'upload_date'

    serializer_class = SubmissionSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = PendingSubmissionPagination

    def get_queryset(self):
        if 'os' in self.kwargs:
            if self.request.user is not None:
                global last_check
                last_check[self.request.user] = datetime.datetime.now()

        # if self.kwargs['os'] not in Run.Platform.values:
        #     raise NotFound

        return Submission.objects.annotate(num_runs=Count('runs', filter=Q(runs__os=self.kwargs['os']))).filter(num_runs=0).order_by('-upload_date')


class RunViewSet(viewsets.ModelViewSet):
    queryset = Run.objects.none()
    serializer_class = RunSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_submission(self):
        submission_id = self.kwargs.get('submission_id')
        submission = Submission.objects.get(id=submission_id)
        if not self.request.user.has_perm('submissions.view_submission', submission):
            raise NotFound
        return submission

    def get_queryset(self):
        submission = self.get_submission()
        return submission.runs.all()

    def get_object(self):
        queryset = self.get_queryset()
        pk = self.kwargs.get('pk')
        try:
            return queryset.get(pk=pk)
        except:
            raise NotFound

    def perform_create(self, serializer):
        if self.request.user is not None:
            global last_check
            last_check[self.request.user] = datetime.datetime.now()

        submission = self.get_submission()
        serializer.save(submission=submission)


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]


class GroupViewSet(viewsets.ModelViewSet):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [permissions.IsAuthenticated]
