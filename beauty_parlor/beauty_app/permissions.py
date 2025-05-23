# permissions.py

from django.contrib.auth.mixins import UserPassesTestMixin


class StaffRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and (
                self.request.user.user_type in ['STAFF', 'ADMIN', 'SUPERADMIN']
        )


class AdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and (
                self.request.user.user_type in ['ADMIN', 'SUPERADMIN']
        )
