from django.contrib.auth.backends import BaseBackend


class DefaultBackend(BaseBackend):
	def authenticate(self, request, **kwargs):
		return None

	def get_user(self, user_id):
		return None

	def get_user_permissions(self, user_obj, obj=None):
		return [
			'submissions.view_submission',
			'runs.view_run',
			'scores.view_score',
		]

	def get_group_permissions(self, user_obj, obj=None):
		return super().get_group_permissions(user_obj, obj)

	def get_all_permissions(self, user_obj, obj=None):
		return super().get_all_permissions(user_obj, obj)

	def has_perm(self, user_obj, perm, obj=None):
		return super().has_perm(user_obj, perm, obj)