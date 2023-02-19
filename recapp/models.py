from typing import Optional, Tuple

import hashlib
import re
from django.core.files.uploadedfile import UploadedFile
from django.db.models.signals import post_save
from django.dispatch import receiver
from enum import Enum
from pathlib import Path

from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

# Create your models here.
from django.utils import timezone
from rest_framework.exceptions import ValidationError


def guess_tas(sub: 'Submission'):
    if re.search(r'(\b|_)tas(\b|_)', sub.name, re.IGNORECASE) is not None:
        return True
    return False


def guess_time(sub: 'Submission') -> Optional[int]:
    match = re.search(r'(\d+)[.,:](\d+)[.,:](\d{3})', sub.name)
    if match is not None:
        return int(match.group(1)) * 60 * 1000 + int(match.group(2)) * 1000 + int(match.group(3))
    match = re.search(r'(\d+)[.,:](\d+)[.,:](\d{2})', sub.name)
    if match is not None:
        return int(match.group(1)) * 60 * 1000 + int(match.group(2)) * 1000 + int(match.group(3)) * 10 + 9
    match = re.search(r'(\d+)[.,:](\d{3})', sub.name)
    if match is not None:
        return int(match.group(1)) * 1000 + int(match.group(2))
    match = re.search(r'(\d+)[.,:](\d{2})', sub.name)
    if match is not None:
        return int(match.group(1)) * 1000 + int(match.group(2)) * 10 + 9
    match = re.search(r'(\d{4}\d*)', sub.name)
    if match is not None:
        return int(match.group(1))
    return None


def guess_time_range(sub: 'Submission') -> Optional[Tuple[int, int]]:
    match = re.search(r'(\d+)[.,:](\d+)[.,:](\d{3})', sub.name)
    if match is not None:
        return \
            int(match.group(1)) * 60 * 1000 + int(match.group(2)) * 1000 + int(match.group(3)), \
            int(match.group(1)) * 60 * 1000 + int(match.group(2)) * 1000 + int(match.group(3))
    match = re.search(r'(\d+)[.,:](\d+)[.,:](\d{2})', sub.name)
    if match is not None:
        return \
            int(match.group(1)) * 60 * 1000 + int(match.group(2)) * 1000 + int(match.group(3)) * 10, \
            int(match.group(1)) * 60 * 1000 + int(match.group(2)) * 1000 + int(match.group(3)) * 10 + 9
    match = re.search(r'(\d+)[.,:](\d{3})', sub.name)
    if match is not None:
        return \
            int(match.group(1)) * 1000 + int(match.group(2)), \
            int(match.group(1)) * 1000 + int(match.group(2))
    match = re.search(r'(\d+)[.,:](\d{2})', sub.name)
    if match is not None:
        return \
            int(match.group(1)) * 1000 + int(match.group(2)) * 10, \
            int(match.group(1)) * 1000 + int(match.group(2)) * 10 + 9
    match = re.search(r'(\d{4}\d*)', sub.name)
    if match is not None:
        return \
            int(match.group(1)), \
            int(match.group(1))
    return None


class Submission(models.Model):
    file = models.FileField('File', upload_to=str(settings.UPLOADS_PATH), max_length=255)
    name = models.TextField('File Name')
    hash = models.TextField('File Hash', max_length=128)
    upload_date = models.DateTimeField('Upload date')
    is_tas = models.BooleanField('Is TAS', default=False)
    expected_time = models.IntegerField('Expected Time', default=None, null=True)

    def __str__(self):
        return f"{self.name}"

    def file_name(self):
        return self.file.name.split("/")[-1]

    def save(self, *args, **kwargs):
        if self.upload_date is None:
            self.upload_date = timezone.now()

        super().save(*args, **kwargs)

    @property
    def best_run(self):
        best = None
        for run in self.runs.all():
            if best is None:
                best = run
                continue
            if best.error is not None and run.error is None:
                best = run
                continue
            if best.error is not None or run.error is not None:
                continue
            if not best.score.success and run.score.success:
                best = run
                continue
            if not best.score.success or not run.score.success:
                continue
            if best.score.score_time > run.score.score_time:
                best = run
                continue
        return best

    @staticmethod
    def create_or_find(form_data):
        if 'file' not in form_data or len(form_data['file']) == 0:
            raise ValidationError("Need file")

        rec: UploadedFile = form_data['file']
        conts = rec.read()
        hash = hashlib.sha256(conts).hexdigest()

        name = rec.name
        if len(name) == 0:
            name = f"Unnamed_{hash[:12]}.rec"

        # See if one exists already
        try:
            sub = Submission.objects.get(hash=hash)
        except Submission.DoesNotExist:
            path = f'{settings.UPLOADS_PATH}/{hash}.rec'
            with open(path, 'wb') as f:
                f.write(conts)
            form_data['file'] = path
            form_data['name'] = name
            form_data['hash'] = hash
            form_data['upload_date'] = timezone.now()
            sub = Submission(**form_data)
            sub.save()

        return sub


@receiver(post_save, sender=Submission)
def check_for_tas(sender, instance, created, **kwargs):
    if created:
        instance.is_tas = guess_tas(instance)
        instance.save()


@receiver(post_save, sender=Submission)
def check_expected_time(sender, instance, created, **kwargs):
    if created and instance.expected_time is None:
        instance.expected_time = guess_time(instance)
        instance.save()


class Score(models.Model):
    success = models.BooleanField('Successful')
    mission = models.TextField('Mission File')
    level_name = models.TextField('Level Name')
    score_time = models.IntegerField('Score Time')
    elapsed_time = models.IntegerField('Elapsed Time')
    bonus_time = models.IntegerField('Bonus Time')
    gem_count = models.IntegerField('Gem Count')
    gem_total = models.IntegerField('Gem Total')
    fps = models.FloatField('Approximate FPS')
    frames_count = models.IntegerField('Frame Count')
    frames_time = models.IntegerField('Frame Time')

    def __str__(self):
        return f"success: {self.success} time: {self.score_time}"

    @property
    def is_desync(self) -> bool:
        if not self.success:
            return False
        if self.run.submission.expected_time is None:
            return False
        if self.score_time == self.run.submission.expected_time:
            return False
        guess = guess_time_range(self.run.submission)
        if guess is None:
            return False
        if self.score_time < guess[0]:
            return True
        if self.score_time > guess[1]:
            return True
        return False


class Run(models.Model):
    submission = models.ForeignKey(Submission, related_name='runs', on_delete=models.CASCADE)
    os = models.TextField('OS', max_length=32)
    run_date = models.DateTimeField('Run Date')
    score = models.OneToOneField(Score, related_name='run', on_delete=models.CASCADE, null=True)
    error = models.TextField('Error Message', null=True)


class Plugin(models.Model):
    file = models.FileField('File', upload_to=str(settings.UPLOADS_PATH), max_length=255)
    name = models.TextField('Plugin Name')
    update_date = models.DateTimeField()
