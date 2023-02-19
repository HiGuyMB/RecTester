from datetime import datetime
from pprint import pprint

import hashlib
from django.contrib.auth.models import User, Group
from django.core.files.uploadedfile import UploadedFile
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.reverse import reverse

from RecTester import settings
from .mixins import WriteOnceMixin
from .models import Submission, Score, Run


class ScoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Score
        fields = ['id', 'success', 'mission', 'level_name', 'score_time', 'elapsed_time', 'bonus_time', 'gem_count', 'gem_total', 'fps', 'frames_count', 'frames_time']


class RunSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    score = ScoreSerializer(many=False, allow_null=True)
    class Meta:
        model = Run
        fields = ['id', 'url', 'os', 'score', 'error']

    def get_url(self, obj):
        submission = obj.submission
        return reverse('run-detail', args=[submission.pk, obj.pk], request=self.context['request'])

    def create(self, validated_data):
        if (validated_data['score'] is None) == (validated_data['error'] is None):
            raise ValidationError('Need either score or error, but not both')

        if validated_data['score'] is not None:
            score_fields = validated_data['score']
            validated_data['score'] = None
            instance = Run(**validated_data)
            instance.score = Score(run=instance, **score_fields)
            instance.score.save()
        else:
            instance = Run(**validated_data)

        instance.run_date = timezone.now()
        instance.submission.runs.add(instance, bulk=False)

        return instance


class SubmissionSerializer(WriteOnceMixin, serializers.HyperlinkedModelSerializer):
    download_url = serializers.HyperlinkedIdentityField(view_name='submission-download')
    runs = RunSerializer(many=True, read_only=True)
    runs_url = serializers.SerializerMethodField()

    class Meta:
        model = Submission
        fields = ['id', 'url', 'name', 'hash', 'file', 'file_name', 'download_url', 'upload_date', 'expected_time', 'runs', 'runs_url']
        read_only_fields = ['upload_date', 'name', 'hash']
        write_once_fields = ['file']
        extra_kwargs = {
            'file': {'write_only': True}
        }

    def create(self, validated_data):
        return Submission.create_or_find(validated_data)

    def get_download_url(self, obj):
        return reverse('submission-download', args=[obj.pk], request=self.context['request'])

    def get_runs_url(self, obj):
        return reverse('run-list', args=[obj.pk], request=self.context['request'])


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ['url', 'username', 'email', 'groups']


class GroupSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Group
        fields = ['url', 'name']


