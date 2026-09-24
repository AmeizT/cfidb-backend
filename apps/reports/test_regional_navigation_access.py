from types import SimpleNamespace
from unittest.mock import Mock, patch
from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory, force_authenticate
from apps.reports.views.region_viewset import RegionViewSet


class RegionalNavigationAccessTests(SimpleTestCase):
    def request(self, authenticated=True, assigned=False, **flags):
        request = APIRequestFactory().get('/region/7/overview/')
        if authenticated:
            regions = Mock()
            regions.filter.return_value.exists.return_value = assigned
            user = SimpleNamespace(is_authenticated=True, is_active=True,
                assigned_regions=regions,
                **dict(dict(is_superuser=False, is_admin=False, is_db_staff=False), **flags))
            force_authenticate(request, user=user)
        return request

    def test_direct_urls_require_region_access_for_every_menu_module(self):
        for action in ['overview', 'finance_aggregate', 'growth_aggregate',
                       'ministry_aggregate', 'leadership_aggregate',
                       'compliance_aggregate', 'risk_aggregate']:
            for authenticated in [False, True]:
                with self.subTest(action=action, authenticated=authenticated), patch(
                    'apps.reports.views.region_viewset.get_object_or_404',
                    return_value=SimpleNamespace(pk=7)):
                    response = RegionViewSet.as_view({'get': action})(
                        self.request(authenticated=authenticated), pk='7')
                    self.assertIn(response.status_code, [401, 403])

    def test_assigned_region_and_existing_global_access_are_preserved(self):
        for flags in [dict(assigned=True), dict(is_admin=True),
                      dict(is_superuser=True), dict(is_db_staff=True)]:
            with self.subTest(flags=flags), patch(
                'apps.reports.views.region_viewset.get_object_or_404',
                return_value=SimpleNamespace(pk=7)), patch.object(
                RegionViewSet, '_dashboard_context', return_value=(Mock(), [])), patch(
                'apps.reports.views.region_viewset.build_region_overview', return_value={}):
                response = RegionViewSet.as_view({'get': 'overview'})(self.request(**flags), pk='7')
                self.assertEqual(response.status_code, 200)
