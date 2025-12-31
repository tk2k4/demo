from django.urls import path, re_path
from . import views

app_name = "youtube"

urlpatterns = [
    path("import-tool/run/", views.import_tool_run, name="import_tool_run"),
    path("import-tool/gpm/", views.get_data_gpm, name="get_data_gpm"),
    path("import-tool/status/", views.get_jobs_status, name="get_jobs_status"),
    path("profiles/import-gpm/", views.import_gpm_profiles, name="import_gpm_profiles"),
    path("profiles/run-tool/", views.run_tool_for_profile, name="run_tool_for_profile"),
    path("dashboard/stats/", views.dashboard_stats, name="dashboard_stats"),
    path("dashboard/export-excel/", views.export_excel, name="export_excel"),
]
