from django.contrib import admin
from .models import Submission, Score
from .templatetags.scores import score


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
	list_display = ('name', 'is_tas', 'upload_date', 'id')
	search_fields = ('name', 'id')


@admin.register(Score)
class ScoreAdmin(admin.ModelAdmin):
	list_display = ('submission', 'level_name', 'os', 'success', 'score_time_formatted', 'elapsed_time_formatted', 'id')

	def submission(self, item):
		return item.run.submission

	def os(self, item):
		return item.run.os

	@admin.display(description='Score Time')
	def score_time_formatted(self, item):
		if not item.success:
			return ""
		return score(item.score_time)

	@admin.display(description='Elapsed Time')
	def elapsed_time_formatted(self, item):
		if not item.success:
			return ""
		return score(item.elapsed_time)
