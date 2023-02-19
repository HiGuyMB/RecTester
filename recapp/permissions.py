from rest_framework.exceptions import MethodNotAllowed, NotFound
from rest_framework.permissions import DjangoModelPermissions


class SubmissionPermissions(DjangoModelPermissions):
	perms_map = {
		'GET': ['submissions.view_submission'],
		'OPTIONS': ['submissions.view_submission'],
		'HEAD': ['submissions.view_submission'],
		'POST': ['submissions.add_submission'],
		'PUT': ['submissions.change_submission'],
		'DELETE': ['submissions.delete_submission'],
	}

	def has_permission(self, request, view):
		user = request.user
		method = request.method
		if method not in self.perms_map:
			raise MethodNotAllowed(method)

		perms = self.perms_map[method]

		if not user.has_perms(perms):
			raise NotFound

		return True


class RunPermissions(SubmissionPermissions):
	perms_map = {
		'GET': ['runs.view_run'],
		'OPTIONS': ['runs.view_run'],
		'HEAD': ['runs.view_run'],
		'POST': ['runs.add_run'],
		'PUT': ['runs.change_run'],
		'DELETE': ['runs.delete_run'],
	}

