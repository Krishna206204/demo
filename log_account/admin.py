from django.contrib import admin
from .models import ActivityLog


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = (
        'log_id',
        'user',
        'action_type',
        'method',
        'path',
        'status_code',
        'ip_address',
        'timestamp',
    )

    list_filter = (
        'action_type',
        'method',
        'status_code',
    )

    search_fields = (
        'user__username',
        'action_type',
        'path',
        'ip_address',
        'description',
    )

    ordering = ('-timestamp',)

    readonly_fields = (
        'log_id',
        'user',
        'action_type',
        'alert_message',
        'path',
        'method',
        'status_code',
        'ip_address',
        'description',
        'timestamp',
    )

    list_per_page = 25